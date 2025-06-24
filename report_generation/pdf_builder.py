from typing import Dict, Any, List
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime
import io
import base64


class PDFBuilder:
    """Helper class for building PDF report components"""

    def __init__(self):
        # Set style for all plots
        plt.style.use('seaborn-v0_8-whitegrid')
        sns.set_palette("husl")

    def create_line_chart(self, data: pd.DataFrame, title: str,
                         ylabel: str, xlabel: str = "Date") -> str:
        """Create a line chart and return as base64 encoded string"""
        fig, ax = plt.subplots(figsize=(10, 6))

        for column in data.columns:
            ax.plot(data.index, data[column], marker='o', label=column)

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.legend()

        # Format x-axis if dates
        if isinstance(data.index, pd.DatetimeIndex):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)

        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return f"data:image/png;base64,{image_base64}"

    def create_bar_chart(self, data: Dict[str, float], title: str,
                        xlabel: str, ylabel: str) -> str:
        """Create a bar chart and return as base64 encoded string"""
        fig, ax = plt.subplots(figsize=(10, 6))

        keys = list(data.keys())
        values = list(data.values())

        bars = ax.bar(keys, values)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}', ha='center', va='bottom')

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return f"data:image/png;base64,{image_base64}"

    def create_heatmap(self, data: pd.DataFrame, title: str) -> str:
        """Create a heatmap and return as base64 encoded string"""
        fig, ax = plt.subplots(figsize=(12, 8))

        sns.heatmap(data, annot=True, fmt='.1f', cmap='RdYlGn_r',
                    center=0, ax=ax, cbar_kws={'label': 'Value'})

        ax.set_title(title, fontsize=16, fontweight='bold')
        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return f"data:image/png;base64,{image_base64}"

    def create_pie_chart(self, data: Dict[str, float], title: str) -> str:
        """Create a pie chart and return as base64 encoded string"""
        fig, ax = plt.subplots(figsize=(8, 8))

        # Filter out zero values
        filtered_data = {k: v for k, v in data.items() if v > 0}

        wedges, texts, autotexts = ax.pie(
            filtered_data.values(),
            labels=filtered_data.keys(),
            autopct='%1.1f%%',
            startangle=90
        )

        ax.set_title(title, fontsize=16, fontweight='bold')

        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return f"data:image/png;base64,{image_base64}"

    def create_gauge_chart(self, value: float, max_value: float,
                          title: str, unit: str = "") -> str:
        """Create a gauge chart for single metric display"""
        fig, ax = plt.subplots(figsize=(6, 4), subplot_kw={'projection': 'polar'})

        # Set the direction of the plot to be counterclockwise
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi / 2)

        # Create the gauge
        theta = np.linspace(0, np.pi, 100)
        r = np.ones_like(theta)

        # Background arc
        ax.plot(theta, r, 'lightgray', linewidth=30)

        # Value arc
        value_theta = theta[0:int(value/max_value * 100)]
        if len(value_theta) > 0:
            color = 'green' if value/max_value > 0.7 else 'orange' if value/max_value > 0.4 else 'red'
            ax.plot(value_theta, r[:len(value_theta)], color, linewidth=30)

        # Add value text
        ax.text(0, -0.2, f'{value:.1f}{unit}', ha='center', va='center',
                fontsize=24, fontweight='bold', transform=ax.transAxes)
        ax.text(0, -0.35, title, ha='center', va='center',
                fontsize=14, transform=ax.transAxes)

        # Remove grid and ticks
        ax.set_ylim(0, 1.5)
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        ax.grid(False)
        ax.spines['polar'].set_visible(False)

        plt.tight_layout()

        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, transparent=True)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return f"data:image/png;base64,{image_base64}"

    def format_table_html(self, df: pd.DataFrame, title: str = "") -> str:
        """Format a DataFrame as an HTML table"""
        html = f"<h3>{title}</h3>" if title else ""

        # Style the DataFrame
        styled_df = df.style.set_properties(**{
            'text-align': 'left',
            'padding': '10px',
            'border': '1px solid #ddd'
        })

        # Add alternating row colors
        styled_df = styled_df.set_table_styles([
            {'selector': 'tr:nth-of-type(odd)', 'props': [('background-color', '#f9f9f9')]},
            {'selector': 'th', 'props': [('background-color', '#4285f4'), ('color', 'white')]}
        ])

        html += styled_df.to_html()
        return html