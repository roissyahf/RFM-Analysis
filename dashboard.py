# import required libraries
import streamlit as st
import pandas as pd
import seaborn as sns
import plotly.express as px


# read dataset
df_all = pd.read_csv('df_terbaru.csv')

# CODE
# convert object to datetime
to_datetime = df_all.loc[:, ('order_purchase_timestamp',
                             'order_approved_at',
                             'order_delivered_carrier_date', 'order_delivered_customer_date',
                             'order_estimated_delivery_date')]

for col in to_datetime:
    df_all[col] = pd.to_datetime(df_all[col], format='%Y-%m-%d %H:%M:%S')

# filter dataset to period of analysis: 2017-02 until 2018-08
df_filtered = df_all[(df_all['order_purchase_timestamp'] >= "2017-02-01 00:00:00") & (df_all['order_purchase_timestamp'] < "2018-09-01 00:00:00")]

# SHOW
sns.set(style='dark')

# add dashboard header
st.header('Starlex E-commerce Dashboard')

# add columns for KPI
col1, col2, col3 = st.columns(3)

with col1:
    total_customers = df_filtered.customer_unique_id.nunique()
    st.metric('Total customers', value=total_customers)

with col2:
    total_orders = df_filtered.order_id.nunique()
    st.metric('Total orders', value=total_orders)

with col3:
    mon = str(df_filtered.payment_value.sum().round()) + ' R$'
    st.metric('Total monetary value', value=mon)

# CODE
# add element:monthly monetary growth, monthly total customers, and monthly total orders
# grouping dataset then renaming it
monthly_agg = df_filtered.groupby(df_filtered['order_purchase_timestamp'].dt.to_period('M')).agg({
        'payment_value': 'sum',
        'order_id': 'nunique',
        'customer_unique_id': 'nunique'
    }).reset_index()

monthly_agg = monthly_agg.rename(columns={
    'order_purchase_timestamp': 'month',
    'payment_value': 'total_payment_value',
    'order_id': 'unique_order_count',
    'customer_unique_id': 'unique_customer_count'
})

# convert 'month' to a string representation
monthly_agg['month'] = monthly_agg['month'].dt.strftime('%Y-%m')

# using pct_change() function to see monthly percentage change
monthly_agg['monthly_payment_value_growth'] = monthly_agg['total_payment_value'].pct_change()

# SHOW
# draw linechart: monthly payment value growth
st.subheader('Monthly payment value growth')
fig = px.line(monthly_agg, x='month', y='monthly_payment_value_growth')
fig.update_xaxes(title='Month')
fig.update_yaxes(title='Total payment Value')
st.plotly_chart(fig, theme='streamlit', use_container_width=True)

# draw lineplot: monthly total customers vs monthly total orders
st.subheader('Monthly total customers vs Monthly total orders')
fig = px.line(monthly_agg, x='month', y=['unique_customer_count', 'unique_order_count'])
fig.update_xaxes(title='Month')
fig.update_yaxes(title='Count')
st.plotly_chart(fig, theme='streamlit', use_container_width=True)

# CODE
# add element: RFM table
def create_rfm_df(df_filtered):
    rfm_df = df_filtered.groupby(by="customer_unique_id", as_index=False).agg({
        "order_purchase_timestamp": 'max',
        "order_id": 'nunique',
        'payment_value': 'sum'
    })

    rfm_df.columns = ['customer_id', 'max_order_timestamp', 'frequency', 'monetary_value']

    rfm_df['max_order_timestamp'] = rfm_df['max_order_timestamp'].dt.date
    recent_date = df_filtered['order_purchase_timestamp'].dt.date.max()
    rfm_df['recency'] = rfm_df['max_order_timestamp'].apply(lambda x: (recent_date - x).days)
    rfm_df.drop("max_order_timestamp", axis=1)

    # segment customers using quartiles
    r_quartiles = pd.qcut(rfm_df['recency'], q=4, labels=range(4,0,-1))
    f_quartiles = pd.qcut(rfm_df['frequency'].rank(method='first'), q=4, labels=range(1,5), duplicates='drop')
    m_quartiles = pd.qcut(rfm_df['monetary_value'].rank(method='first'), q=4, labels=range(1,5), duplicates='drop')

    # building RFM segments: R | F | M
    rfm_df = rfm_df.assign(R=r_quartiles,F=f_quartiles,M=m_quartiles)

    # building RFM score: | R + F + M |
    rfm_df['RFM_segment'] = rfm_df['R'].astype(str) +\
                      rfm_df['F'].astype(str) +\
                      rfm_df['M'].astype(str)

    rfm_df['RFM_score'] = rfm_df[['R','F','M']].sum(axis=1)

    return rfm_df

# create rfm_df with columns: customer_id | recency | frequency | monetary_value | R | F | M | RFM_segment | RFM_score
rfm_df = create_rfm_df(df_filtered)

def define_rfm_segment(rfm_df):
    seg_map = {
    r'[1-2][1-2]': 'Hibernating', 
    r'[1-2]3': 'At Risk', 
    r'[1-2]4': 'Can\'t Loose', 
    r'31': 'About to Sleep', 
    r'33': 'Need Attention', 
    r'[3-4][4-5]': 'Loyal Customers', 
    r'41': 'Promising', 
    r'32': 'New Customers',
    r'[4-5]2': 'Potential Loyalists', 
    r'43': 'Champions' 
}
    rfm_df['Segment'] = rfm_df['R'].astype(str) + rfm_df['F'].astype(str)
    rfm_df['Segment check'] = rfm_df['Segment']
    rfm_df['Segment'] = rfm_df['Segment'].replace(seg_map, regex=True)

    return rfm_df

# defining RFM segment category
rfm_segments = define_rfm_segment(rfm_df)

# summarize RFM mean in each defined segments
rfm_summary = rfm_segments.groupby('Segment').agg({
    'recency': 'mean',
    'frequency': 'mean',
    'monetary_value': 'mean'}).round()
rfm_summary = rfm_summary.sort_values(ascending=False, by='monetary_value')

# count of customers in each defined segments
rfm_cust_count = rfm_segments.copy()
rfm_cust_count = rfm_cust_count.reset_index(inplace=True)
rfm_cust_count = rfm_segments[['Segment','customer_id']].groupby(['Segment']).count()
# create new df to easier making plot
rfm_cust_plot = rfm_cust_count.sort_values(ascending=True, by='customer_id').reset_index()
rfm_cust_plot.rename(columns={'Segment': 'Segment Type',
                        'customer_id': 'Count of Customer'}, inplace=True)

# SHOW
# draw the bar plot
st.subheader('Customer segmentation')
fig = px.bar(rfm_cust_plot, x='Count of Customer', y='Segment Type')
st.plotly_chart(fig, theme='streamlit', use_container_width=True)

# visualize the rfm summary df
st.subheader('Mean of RFM in each segments')
st.dataframe(rfm_summary)

# END