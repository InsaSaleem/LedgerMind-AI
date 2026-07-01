import matplotlib
matplotlib.use('Agg') # Headless backend
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64

def generate_chart(df, chart_type):
    """
    Generates a chart using Matplotlib and returns it as a base64 encoded image string.
    chart_type can be 'category_pie', 'trend_line', or 'bar'
    """
    plt.figure(figsize=(8, 5))
    
    # Custom styling colors
    colors = ['#00D26A', '#0A0A0A', '#E0E0E0', '#4CAF50', '#81C784']
    
    if chart_type == 'category_pie' and 'Category' in df.columns:
        cat_sums = df.groupby('Category')['Amount'].sum()
        if not cat_sums.empty:
            plt.pie(cat_sums, labels=cat_sums.index, autopct='%1.1f%%', colors=colors, startangle=140)
            plt.title('Spending by Category')
    elif chart_type == 'trend_line':
        df['Date'] = pd.to_datetime(df['Date'])
        trend = df.groupby('Date')['Amount'].sum().sort_index()
        plt.plot(trend.index, trend.values, marker='o', color='#00D26A', linewidth=2)
        plt.title('Spending Trend Over Time')
        plt.xlabel('Date')
        plt.ylabel('Amount')
        plt.xticks(rotation=45)
    else: # Default bar chart
        if 'Category' in df.columns:
            cat_sums = df.groupby('Category')['Amount'].sum()
            cat_sums.plot(kind='bar', color='#00D26A')
            plt.title('Spending by Category (Bar)')
            plt.xticks(rotation=45)
        else:
            plt.text(0.5, 0.5, "Insufficient Data for Chart", ha='center', va='center')

    plt.tight_layout()
    
    # Save to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    # Encode to base64
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"
