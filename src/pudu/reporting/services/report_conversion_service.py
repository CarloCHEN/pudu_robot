import asyncio
from pathlib import Path

async def html_to_pdf(html_file, output_pdf=None):
    """Convert HTML to PDF with charts rendered"""
    if not output_pdf:
        output_pdf = html_file.replace('.html', '.pdf')

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            html_path = Path(html_file).resolve()
            await page.goto(f"file://{html_path}")

            # Wait for charts to load
            await page.wait_for_timeout(5000)

            await page.pdf(
                path=output_pdf,
                format='A4',
                print_background=True,
                margin={'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
            )

            await browser.close()
            print(f"PDF created: {output_pdf}")
            return True

    except ImportError:
        print("Install: pip install playwright && playwright install chromium")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def convert_html_to_pdf(html_file, output_pdf=None):
    """Wrapper function for terminal use"""
    return asyncio.run(html_to_pdf(html_file, output_pdf))

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python script.py input.html [output.pdf]")
        sys.exit(1)

    html_file = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None

    success = convert_html_to_pdf(html_file, output_pdf)
    if not success:
        sys.exit(1)