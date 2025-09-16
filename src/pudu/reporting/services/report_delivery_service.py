import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import json

import aioboto3
from botocore.exceptions import ClientError

from ..core.report_config import ReportConfig, DeliveryMethod

logger = logging.getLogger(__name__)

class ReportDeliveryService:
    """Service for delivering generated reports via email or storing for in-app access"""

    def __init__(self, region: str = 'us-east-2'):
        """Initialize delivery service"""
        self.region = region

        # Configure S3 bucket based on region
        if region == 'us-east-1':
            self.reports_bucket = "monitor-reports-test-archive"
        else:  # us-east-2 and default
            self.reports_bucket = "monitor-reports-archive"

        # aioboto3 session for async operations
        self.session = aioboto3.Session()

        logger.info(f"Initialized ReportDeliveryService for region {region}, bucket: {self.reports_bucket}")

    async def deliver_report(self, report_content: Union[str, bytes], metadata: Dict[str, Any],
                            report_config: ReportConfig, content_type: str = 'text/html',
                            file_extension: str = '.html') -> Dict[str, Any]:
        """
        Deliver report based on configuration

        Args:
            report_content: Generated report content (HTML string or PDF bytes)
            metadata: Report metadata
            report_config: Report configuration with delivery preferences
            content_type: Content type for S3 storage ('text/html' or 'application/pdf')
            file_extension: File extension ('.html' or '.pdf')

        Returns:
            Dict with delivery results
        """
        logger.info(f"Delivering {content_type} report for customer {report_config.customer_id} via {report_config.delivery.value}")

        delivery_results = {
            'success': False,
            'delivery_method': report_config.delivery.value,
            'storage_url': None,
            'email_sent': False,
            'error': None,
            'content_type': content_type,
            'file_extension': file_extension
        }

        try:
            # Always store report in S3 for backup/history
            storage_result = await self._store_report_in_s3(
                report_content, metadata, report_config, content_type, file_extension
            )
            delivery_results.update(storage_result)

            # Deliver based on method
            if report_config.delivery == DeliveryMethod.EMAIL:
                email_result = await self._deliver_via_email(
                    report_content, metadata, report_config,
                    delivery_results.get('storage_url'), content_type
                )
                delivery_results.update(email_result)
            else:
                # In-app delivery (already stored in S3)
                delivery_results['success'] = storage_result.get('success', False)
                logger.info(f"Report stored for in-app access: {delivery_results.get('storage_url')}")

            return delivery_results

        except Exception as e:
            logger.error(f"Error delivering report: {e}")
            delivery_results['error'] = str(e)
            return delivery_results

    async def _store_report_in_s3(self, report_content: Union[str, bytes], metadata: Dict[str, Any],
                                 report_config: ReportConfig, content_type: str = 'text/html',
                                 file_extension: str = '.html') -> Dict[str, Any]:
        """Store report in S3 for archival and in-app access"""
        try:
            # Generate S3 key with proper organization
            timestamp = datetime.now()
            s3_key = self._generate_report_s3_key(
                report_config.customer_id, metadata, timestamp, file_extension
            )

            # Prepare content for upload
            if isinstance(report_content, str):
                body = report_content.encode('utf-8')
            else:
                body = report_content  # Already bytes (for PDF)

            async with self.session.client('s3', region_name=self.region) as s3_client:
                # Store report
                await s3_client.put_object(
                    Bucket=self.reports_bucket,
                    Key=s3_key,
                    Body=body,
                    ContentType=content_type,
                    Metadata={
                        'customer_id': report_config.customer_id,
                        'generation_time': metadata.get('generation_time', ''),
                        'detail_level': report_config.detail_level.value,
                        'report_type': 'robot_performance',
                        'api_version': '1.0.0',
                        'output_format': file_extension.replace('.', '').upper()
                    }
                )

                # Store metadata separately
                metadata_key = s3_key.replace(file_extension, '_metadata.json')
                enhanced_metadata = {
                    **metadata,
                    'storage_info': {
                        'bucket': self.reports_bucket,
                        'region': self.region,
                        'stored_at': timestamp.isoformat(),
                        'content_type': content_type,
                        'file_extension': file_extension
                    }
                }

                await s3_client.put_object(
                    Bucket=self.reports_bucket,
                    Key=metadata_key,
                    Body=json.dumps(enhanced_metadata, indent=2).encode('utf-8'),
                    ContentType='application/json'
                )

            # Generate access URL
            storage_url = f"https://{self.reports_bucket}.s3.{self.region}.amazonaws.com/{s3_key}"

            logger.info(f"Stored {content_type} report in S3: {storage_url}")
            return {
                'success': True,
                'storage_url': storage_url,
                's3_key': s3_key,
                'bucket': self.reports_bucket,
                'region': self.region
            }

        except ClientError as e:
            logger.error(f"Error storing report in S3: {e}")
            return {
                'success': False,
                'error': f"S3 storage failed: {e}"
            }

    async def _deliver_via_email(self, report_content: Union[str, bytes], metadata: Dict[str, Any],
                               report_config: ReportConfig, storage_url: Optional[str] = None,
                               content_type: str = 'text/html') -> Dict[str, Any]:
        """Deliver report via email"""
        try:
            # Prepare email content
            subject = self._generate_email_subject(metadata, report_config, content_type)
            body_text, body_html = self._generate_email_body(
                metadata, report_config, storage_url, content_type
            )

            # Prepare attachment if it's a PDF
            attachments = []
            if content_type == 'application/pdf' and isinstance(report_content, bytes):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"robot_report_{report_config.customer_id}_{timestamp}.pdf"
                attachments.append({
                    'filename': filename,
                    'content': report_content,
                    'content_type': 'application/pdf'
                })

            # Send to all recipients
            email_results = []

            async with self.session.client('ses', region_name=self.region) as ses_client:
                for recipient in report_config.email_recipients:
                    try:
                        # Prepare email message
                        email_message = {
                            'Source': 'reports@robotmanagement.com',  # Configure this
                            'Destination': {'ToAddresses': [recipient]},
                            'Message': {
                                'Subject': {'Data': subject},
                                'Body': {
                                    'Text': {'Data': body_text},
                                    'Html': {'Data': body_html}
                                }
                            }
                        }

                        # Add attachment for PDF
                        if attachments:
                            # For SES with attachments, we need to use raw email
                            raw_email = self._create_raw_email_with_attachment(
                                'reports@robotmanagement.com',
                                recipient,
                                subject,
                                body_text,
                                body_html,
                                attachments[0]
                            )

                            response = await ses_client.send_raw_email(
                                Source='reports@robotmanagement.com',
                                Destinations=[recipient],
                                RawMessage={'Data': raw_email}
                            )
                        else:
                            response = await ses_client.send_email(**email_message)

                        email_results.append({
                            'recipient': recipient,
                            'success': True,
                            'message_id': response['MessageId']
                        })
                        logger.info(f"Email sent to {recipient}: {response['MessageId']}")

                    except ClientError as e:
                        email_results.append({
                            'recipient': recipient,
                            'success': False,
                            'error': str(e)
                        })
                        logger.error(f"Failed to send email to {recipient}: {e}")

            # Determine overall email success
            successful_emails = sum(1 for result in email_results if result['success'])
            total_emails = len(email_results)

            return {
                'email_sent': successful_emails > 0,
                'email_results': email_results,
                'emails_successful': successful_emails,
                'emails_total': total_emails,
                'success': successful_emails == total_emails
            }

        except Exception as e:
            logger.error(f"Error in email delivery: {e}")
            return {
                'email_sent': False,
                'error': f"Email delivery failed: {e}",
                'success': False
            }

    def _create_raw_email_with_attachment(self, from_email: str, to_email: str,
                                        subject: str, text_body: str, html_body: str,
                                        attachment: Dict[str, Any]) -> bytes:
        """Create raw email message with PDF attachment"""
        import email.mime.multipart
        import email.mime.text
        import email.mime.application
        import base64

        # Create the multipart message
        msg = email.mime.multipart.MIMEMultipart('mixed')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Create multipart alternative for text and HTML
        msg_body = email.mime.multipart.MIMEMultipart('alternative')

        # Add text part
        text_part = email.mime.text.MIMEText(text_body, 'plain', 'utf-8')
        msg_body.attach(text_part)

        # Add HTML part
        html_part = email.mime.text.MIMEText(html_body, 'html', 'utf-8')
        msg_body.attach(html_part)

        # Attach the body to the main message
        msg.attach(msg_body)

        # Add PDF attachment
        pdf_attachment = email.mime.application.MIMEApplication(
            attachment['content'],
            _subtype='pdf'
        )
        pdf_attachment.add_header(
            'Content-Disposition',
            'attachment',
            filename=attachment['filename']
        )
        msg.attach(pdf_attachment)

        return msg.as_bytes()

    def _generate_report_s3_key(self, customer_id: str, metadata: Dict[str, Any],
                               timestamp: datetime, file_extension: str = '.html') -> str:
        """Generate organized S3 key for report storage"""
        # Organization: reports/{customer_id}/{year}/{month}/{timestamp}_report.{ext}
        year = timestamp.year
        month = timestamp.month
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')

        file_type = file_extension.replace('.', '')
        return f"reports/{customer_id}/{year:04d}/{month:02d}/{timestamp_str}_robot_performance_report.{file_type}"

    def _generate_email_subject(self, metadata: Dict[str, Any], report_config: ReportConfig,
                               content_type: str = 'text/html') -> str:
        """Generate email subject line"""
        period = metadata.get('date_range', {})
        start_date = period.get('start', '')
        end_date = period.get('end', '')

        format_type = "PDF" if content_type == 'application/pdf' else "HTML"

        if start_date and end_date:
            date_str = f" ({start_date} to {end_date})"
        else:
            date_str = ""

        return f"Robot Management Report{date_str} - {report_config.detail_level.value.title()} Analysis [{format_type}]"

    def _generate_email_body(self, metadata: Dict[str, Any], report_config: ReportConfig,
                           storage_url: Optional[str] = None, content_type: str = 'text/html') -> Tuple[str, str]:
        """Generate email body (text and HTML)"""
        period = metadata.get('date_range', {})
        robots_count = metadata.get('robots_included', 0)
        records_processed = metadata.get('total_records_processed', 0)
        generation_time = metadata.get('generation_time', '')

        format_type = "PDF" if content_type == 'application/pdf' else "HTML"
        attachment_note = " (attached as PDF)" if content_type == 'application/pdf' else ""

        # Check if there was a format fallback
        fallback_note = ""
        if hasattr(report_config, 'format_fallback') and report_config.format_fallback:
            fallback_note = f"\n\nNote: PDF was requested but delivered as HTML due to unavailable PDF generation capabilities."

        # Text version
        body_text = f"""
        Robot Management Report

        Report Period: {period.get('start', '')} to {period.get('end', '')}
        Detail Level: {report_config.detail_level.value.title()}
        Format: {format_type}
        Robots Included: {robots_count}
        Records Processed: {records_processed}
        Generated: {generation_time}

        Content Categories:
        {chr(10).join(['- ' + cat.replace('-', ' ').title() for cat in report_config.content_categories])}

        {'View online: ' + storage_url if storage_url else ''}
        {attachment_note}
        {fallback_note}

        This is an automated report from the Robot Management System.
        """.strip()

        # HTML version
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .metric {{ margin: 10px 0; }}
                .footer {{ background: #ecf0f1; padding: 15px; text-align: center; font-size: 0.9em; }}
                .format-badge {{ background: #3498db; color: white; padding: 3px 8px; border-radius: 3px; font-size: 0.8em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Robot Management Report <span class="format-badge">{format_type}</span></h1>
            </div>
            <div class="content">
                <p><strong>Your robot management report is ready!</strong>{attachment_note}</p>

                <div class="metric"><strong>Report Period:</strong> {period.get('start', '')} to {period.get('end', '')}</div>
                <div class="metric"><strong>Detail Level:</strong> {report_config.detail_level.value.title()}</div>
                <div class="metric"><strong>Format:</strong> {format_type}</div>
                <div class="metric"><strong>Robots Included:</strong> {robots_count}</div>
                <div class="metric"><strong>Records Processed:</strong> {records_processed}</div>
                <div class="metric"><strong>Generated:</strong> {generation_time}</div>

                <h3>Content Categories:</h3>
                <ul>
                {''.join([f'<li>{cat.replace("-", " ").title()}</li>' for cat in report_config.content_categories])}
                </ul>

                {f'<p><a href="{storage_url}" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Report Online</a></p>' if storage_url else ''}
            </div>
            <div class="footer">
                <p>This is an automated report from the Robot Management System.</p>
            </div>
        </body>
        </html>
        """.strip()

        return body_text, body_html

    async def get_report_history(self, customer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get report history for a customer from S3"""
        try:
            # List objects for this customer
            prefix = f"reports/{customer_id}/"

            async with self.session.client('s3', region_name=self.region) as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self.reports_bucket,
                    Prefix=prefix,
                    MaxKeys=limit
                )

            reports = []
            for obj in response.get('Contents', []):
                # Skip metadata files
                if obj['Key'].endswith('_metadata.json'):
                    continue

                # Determine format from file extension
                if obj['Key'].endswith('.pdf'):
                    format_type = 'PDF'
                    content_type = 'application/pdf'
                else:
                    format_type = 'HTML'
                    content_type = 'text/html'

                report_info = {
                    'key': obj['Key'],
                    'url': f"https://{self.reports_bucket}.s3.{self.region}.amazonaws.com/{obj['Key']}",
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'filename': obj['Key'].split('/')[-1],
                    'format': format_type,
                    'content_type': content_type
                }
                reports.append(report_info)

            # Sort by last modified (newest first)
            reports.sort(key=lambda x: x['last_modified'], reverse=True)

            return reports

        except ClientError as e:
            logger.error(f"Error getting report history: {e}")
            return []

    async def delete_report(self, customer_id: str, report_key: str) -> Dict[str, Any]:
        """Delete a stored report"""
        try:
            # Verify the report belongs to the customer
            if not report_key.startswith(f"reports/{customer_id}/"):
                return {
                    'success': False,
                    'error': 'Unauthorized: Report does not belong to customer'
                }

            async with self.session.client('s3', region_name=self.region) as s3_client:
                # Delete report and metadata
                await s3_client.delete_object(Bucket=self.reports_bucket, Key=report_key)

                # Delete metadata file (try both extensions)
                for ext in ['.html', '.pdf']:
                    if report_key.endswith(ext):
                        metadata_key = report_key.replace(ext, '_metadata.json')
                        try:
                            await s3_client.delete_object(Bucket=self.reports_bucket, Key=metadata_key)
                            break
                        except ClientError:
                            pass  # Metadata file might not exist

            logger.info(f"Deleted report: {report_key}")
            return {
                'success': True,
                'message': 'Report deleted successfully'
            }

        except ClientError as e:
            logger.error(f"Error deleting report: {e}")
            return {
                'success': False,
                'error': str(e)
            }