######################### IMPORT LIBRARY  ###############################
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta

######################### FUNCTIONS UTILS ###############################
## structure df to optimize storage
def structure_data(df_: pd.DataFrame, col_type_: dict):
    for col in df_.columns:
        if col in col_type_.keys():
            if col_type_[col] == datetime:
                df_[col] = pd.to_datetime(df_[col])
            elif col_type_[col] == 'date':
                df_[col] = pd.to_datetime(df_[col]).dt.date
            elif type(col_type_[col]) == list:
                if col_type_[col][0] == 'date':
                    df_[col] = pd.to_datetime(df_[col],format=col_type_[col][1]).dt.date
            elif col_type_[col] == 'str' or col_type_[col] == str:
                df_[col] = df_[col].astype(pd.StringDtype())
            else:
                df_[col] = df_[col].astype(col_type_[col])
        elif df_[col].dtype in ['str','float','int64','int32','int8']:
            pass
        elif df_[col].dtype == 'object':
            df_[col] = df_[col].astype(pd.StringDtype())
        else:
            pass
    return df_
## category pandas df
def index_cate_df(df_,list_col_):
    for col_ in list_col_:
        exec(f'df_.{col_} = pd.Categorical(df_.{col_})')
        exec(f'''df_['{col_}_ID'] = df_.{col_}.cat.codes''')
    return df_
############################################### Transaction Types Issues

st.write("""
# 1. Transaction Types:
### Business Situations:
- Business are unsure what txn_type_code in csv file which is extracted from database means (those are 1,2,3,4,5,6,7)
- Business believes that the transaction types contained are:
  - Internal Transfers
  - Interbank Transfer
  - Saving Account Withdrawal
  - Auto Recurring Savings Account Contribution
  - Manual Savings Account Contribution
  - Phone Top-Up
  - Gift Payments
  
### Situation Analysis
- From business information:
  - **3 transaction types** with **positive amount**: Saving Account Withdrawal, Auto Recurring Savings Account Contribution, Gift Payments
  - **3 transaction types** with **negative amount**: Interbank Transfer, Manual Savings Account Contribution, Phone Top-Up
  - **1 transaction types** with both **positive and negative amount**: Internal Transfers
  - There are some **transaction types** in practice that a digital bank **may have but not be mentioned** from business such as: Cash Top up, ATM withdrawal, POS transaction with debit card, Loan payment,...
- From csv file:
  - Transaction type 1 is the only one included positive and negative transaction amount. This can imply that **txn_type_code 1 may be Internal Transfer**
  - Transaction **type 2,5 only have negative amount**. And **type 3,4,6,7 only have positive amount**.
  - The csv file was extracted from database with **lack of conditions during extracting**, so that it maybe not reflect all transaction types in SuperBank
  - There are **80 records** of transaction with **0 amount**
### Executive Summary:
  - **Retrieve query history** of the intern, then we can understand underground logic of his tasks
  - Take some **sample cases** from transaction csv file that Business absolutely understand which type of transaction it is then mapping together
  - Ask business for more types of transactions operated by SuperBank so that we can have a better **full picture of transaction type**
  - In case some transaction types are still not defined, execute these types of transaction in real life to make sure we can define them
  - Clarify with transaction relevant team (IT, transaction core system, Business, ..) to retrieve Business Requirements Document (**BRD**)/ other documents that can help SuperBank define transaction type code
  - **Develop documents process** so that any reports/extracted file will be all clarified and shared in SuperBank 
  """)

st.write("""*Based on transaction type code situation above, there would be not many analysis idea that I can share in the best way. With existing data and our SuperBank information, there are several points out below*""") 

################## READ & TRANSFORM DATA #####################
# read & structure data from txn_history_dummysample.csv
# txn = pd.read_csv(os.getcwd()+r"\txn_history_dummysample.csv")
st.write("""
# 2. Exploratory data analysis:
""")
txn_file = st.file_uploader("Upload your txn_history_dummysample.csv here to view the presentation!", type={"csv"})
if txn_file is not None and txn_file:
    txn = pd.read_csv(txn_file)
    txn = structure_data(txn ,{'account_id':'str'
                                # ,'date_of_birth':['date','%Y-%m-%d']
                                ,'date_of_birth': datetime
                                ,'txn_ts':datetime
                                ,'txn_type_code':'int8'
                                })
    st.write(f"""*Transactions data from {format(txn['txn_ts'].min(),'%Y %B')} - {format(txn['txn_ts'].max(),'%Y %B')}*""")
    txn['age'] = txn['date_of_birth'].apply(lambda x: datetime.now().year - x.year)
    txn['txn_hour'] = txn['txn_ts'].apply(lambda x: x.hour)
    txn['txn_day'] = txn['txn_ts'].apply(lambda x: x.day)
    txn['txn_weekday'] = (txn['txn_ts'].dt.weekday).apply(lambda x: "Sun" if x==6 \
                                                                    else "Sat" if x==5 \
                                                                    else "Fri" if x==4 \
                                                                    else "Thu" if x==3 \
                                                                    else "Wed" if x==2 \
                                                                    else "Tue" if x==1 \
                                                                    else "Mon" if x==0
                                                                    else "unknown")
    txn['txn_month'] = txn['txn_ts'].apply(lambda x: x.month)
    txn['txn_amount_abs'] = txn['txn_amount'].apply(lambda x: abs(x))
    age_group_bins= [0,18,23,35,56, 120]
    age_group_labels = ['[<18]','[18-22]','[23-34]','[35-55]', '[>55]']
    txn['age_group'] = pd.cut(txn['age'], bins=age_group_bins, labels=age_group_labels, right=False, ordered =True)
    txn["txn_de_cre_group"] = "Unknown"
    txn["txn_de_cre_group"] = txn["txn_de_cre_group"].case_when([
        (txn.eval("txn_amount >= 0"), "Incoming Transaction")
        ,(txn.eval("txn_amount < 0"), "Outgoing Transaction")
    ])

    ##balance
    txn['txn_date'] = txn['txn_ts'].dt.normalize()
    bln_mapping = txn[['account_id','age','age_group']].drop_duplicates()
    bln_ = txn[['account_id','txn_date','txn_weekday','txn_amount']].groupby(['account_id','txn_date']).agg('sum').reset_index()
    bln = pd.merge(bln_, bln_mapping, how='left', on='account_id')

    ##transaction size
    txn['txn_date'] = txn['txn_ts'].dt.normalize()
    txnsize_mapping = txn[['account_id','age','age_group']].drop_duplicates()
    txnsize_ = txn[['account_id','txn_date','txn_month','txn_day','txn_amount_abs']].groupby(['account_id','txn_date','txn_month','txn_day']).agg('sum').reset_index()
    txnsize = pd.merge(txnsize_, txnsize_mapping, how='left', on='account_id')

    ##negative amount types
    #txn[txn['txn_amount']<0][['txn_type_code']].drop_duplicates()
    ##positive amount types
    #txn[txn['txn_amount']>=0][['txn_type_code']].drop_duplicates()

    ############################################# EXPLORE DATA

    st.markdown("### 2.1. Demographic Information")

    # col1, col2 = st.columns(2)
    # name_selection = col1.multiselect('Select Transaction Type Code: ', sorted(txn.txn_type_code.unique().tolist()), key='txn_type_code')


    st.markdown("##### Customers Age Group (from Transactions)")
    st.markdown(f"""- **:green[#Customers]** in Age Group **:green[[23-34] are ~5 times]** more than group **:green[[35-55]]**""")
    fig1, ax1 = plt.subplots()
    chart_df = bln_mapping.groupby('age_group').count().reset_index()
    ax1 = px.pie(chart_df[['age_group','account_id']], values='account_id', names='age_group',category_orders=chart_df['age_group'])
    st.plotly_chart(ax1, use_container_width=True)

        
    st.markdown("### 2.2. How Customers use SuperBank service?")
    st.markdown("##### #Transactions per Customer Age Group")
    fig_col1, fig_col2 = st.columns(2)
    with fig_col1:
        de_cre_selection = fig_col1.multiselect('Select Incoming/Outgoing Transactions: ', sorted(txn.txn_de_cre_group.unique().tolist()), key='txn_de_cre_group')
    with fig_col2:
        fig2, ax2 = plt.subplots()
        chart_df = (txn[txn['txn_de_cre_group'].isin(de_cre_selection)] if len(de_cre_selection)!=0 else txn).groupby('age_group').count().reset_index()
        chart_df['count'] = chart_df['age']
        chart_df = chart_df.sort_values(by='count',ascending=False)
        per_val = round((chart_df[chart_df['age_group'].isin(['[23-34]','[35-55]'])]['count'].sum())*100/(chart_df['count'].sum()),1)
        st.markdown(f"""- About **:green[{per_val:,}% transactions]** of total come from Customers in **:green[Age Group [23-34] and [35-55]]**""")
        ax2 = px.pie(chart_df[['age_group','count']], values='count', names='age_group',category_orders=chart_df['age_group'])
        st.plotly_chart(ax2, use_container_width=True)
        
    st.markdown("##### Average Balance per Customer Age Group")   
    fig_col3, fig_col4, fig_col5 = st.columns(3)
    chart_df = bln.groupby('account_id').agg({'age_group':'min','txn_amount':'mean'}).reset_index()\
                    .groupby('age_group').agg({'txn_amount':'mean'}).reset_index()
    chart_df['avg_balance'] = chart_df['txn_amount'].fillna(0)
    chart_df['avg_balance'] = chart_df['avg_balance'].apply(lambda x: round(x,0))
    chart_df1 = chart_df.drop(columns=['txn_amount'])
    with fig_col3:
        fig3 =px.bar(chart_df1,x='avg_balance',y='age_group', orientation='h',width=400)
        st.write(fig3)
    with fig_col5:
        fig5, ax5 = plt.subplots(4,4)
        chart_df1

    st.markdown("##### Average Transaction Size per Customer Age Group")   
    fig_col6, fig_col7, fig_col8 = st.columns(3)
    chart_df = txnsize.groupby('account_id').agg({'age_group':'min','txn_amount_abs':'mean'}).reset_index()\
                    .groupby('age_group').agg({'txn_amount_abs':'mean'}).reset_index()
    chart_df['avg_transaction_size'] = chart_df['txn_amount_abs'].fillna(0)
    chart_df['avg_transaction_size'] = chart_df['avg_transaction_size'].apply(lambda x: round(x,0))
    chart_df = chart_df.drop(columns=['txn_amount_abs'])
    with fig_col6:
        fig6 =px.bar(chart_df,x='avg_transaction_size',y='age_group', orientation='h',width=400)
        st.write(fig6)
    with fig_col8:
        fig8, ax8 = plt.subplots(4,4)
        chart_df
    st.write(f"""Insights:""")
    st.write(f"""- Customer **:green[Age Group [23-34]]** which is top 1 number of customers has average **:green[balance {int(chart_df1[chart_df1['age_group'].isin(['[23-34]'])]['avg_balance'].values[0]):,}]**
- Customer **:green[Age Group [35-55]]** which is top 2 number of customers has average **:green[balance {int(chart_df1[chart_df1['age_group'].isin(['[35-55]'])]['avg_balance'].values[0]):,}]** and average **:green[transaction size {int(chart_df[chart_df['age_group'].isin(['[35-55]'])]['avg_transaction_size'].values[0]):,}]**""")
    st.write(f"""Recommends:""")
    st.write(f"""- **:green[Encourage]** Customer Age Group **:green[[23-34] higher their balance]** with average **:green[transaction size {int(chart_df[chart_df['age_group'].isin(['[23-34]'])]['avg_transaction_size'].values[0]):,}]** by campaigns (ex: automatically electric and water bill payment, school/course payment, discount annual account service fee, beautiful card number/account number discount, Term Deposit promotion if maintain average balance, Bank at work (salary account), etc.)""")
    st.write(f"""- **:green[Increase #Customers]** in Age Group **:green[[35-55]]** to achieve more total balance amount from this good average balance.""")

    st.markdown("##### Which type of transaction Customers made the most?")   
    fig_col9, fig_col10 = st.columns(2)
    with fig_col9:
        chart_df = txn[txn['txn_de_cre_group']=='Incoming Transaction'][['txn_type_code','txn_amount_abs']].groupby(['txn_type_code']).agg('sum').reset_index()
        st.markdown(f"**:green[94.1%]** number of **:green[incoming transactions]** come from **:green[transaction type 1]** (supposed to be Internal Transfer type)")  
        fig9, ax9 = plt.subplots()
        ax9 = px.pie(chart_df[['txn_type_code','txn_amount_abs']], values='txn_amount_abs', names='txn_type_code')
        st.plotly_chart(ax9, use_container_width=True)
    with fig_col10:
        st.markdown(f"**:green[85%]** number of **:green[outgoing transactions]** for **:green[type 2]**")
        fig10, ax10 = plt.subplots()
        chart_df = txn[txn['txn_de_cre_group']=='Outgoing Transaction'][['txn_type_code','txn_amount_abs']].groupby(['txn_type_code']).agg('sum').reset_index()
        ax10 = px.pie(chart_df[['txn_type_code','txn_amount_abs']], values='txn_amount_abs', names='txn_type_code')
        st.plotly_chart(ax10, use_container_width=True)
    st.write(f"""Recommends:""")
    st.write(f"""- Advertise/Push up activities of those 2 transaction type 1 and type 2, that can lead to increase total balance""")
            
    st.markdown("##### Which day in week has total balance at top?")
    chart_df = txn[['txn_weekday','txn_amount']].groupby(['txn_weekday']).agg('sum').reset_index()
    chart_df = chart_df.rename(columns={"txn_amount": "total_balance"})
    fig10 =px.bar(chart_df,x='txn_weekday',y='total_balance', orientation='v')
    fig10.update_xaxes(categoryorder='array', categoryarray= ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'])
    st.write(fig10)
    st.write(f"""Insights:
- **:green[Wednesday, Thursday, Friday]** are **:green[top 3]** day have **:green[high total balance]**
- **:green[Sunday]** has **:green[negative total balance]**""")
    st.write(f"""Recommends:
- Encourage Customers make transactions more in Wednesday, Thursday, Friday and not execute campaigns in Sunday""")  

    st.markdown("##### Total Transaction amount per from Jan 2021 - March 2021")
    fig_col11, fig_colX = st.columns(2)
    with fig_col11:
        chart_df = txnsize[txnsize['txn_month'].isin([1,2,3])][['txn_month','txn_amount_abs']].groupby(['txn_month']).agg({'txn_amount_abs':'sum'}).reset_index()
        chart_df = chart_df.rename(columns={"txn_amount_abs": "total_transaction_amount"})
        fig11 =px.bar(chart_df,x='txn_month',y='total_transaction_amount', orientation='v',width=300)
        fig11.update_xaxes(categoryorder='array', categoryarray= [1,2,3])
        st.write(fig11)
    with fig_colX:
        st.write(f"""Total transactions size lightly decreased in February 2021""")
    fig_col13,fig_colX = st.columns(2)
    with fig_col13:
        month_selection = fig_col13.multiselect('Select Month: ', sorted(chart_df.txn_month.unique().tolist()), key='txn_month',default=[2])
    chart_df = txnsize[txnsize['txn_month'].isin(month_selection if len(month_selection) != 0 else [1,2,3])][['txn_day','txn_amount_abs']].groupby(['txn_day']).agg({'txn_amount_abs':'sum'}).reset_index()
    chart_df = chart_df.rename(columns={"txn_amount_abs": "total_transaction_amount"})
    fig14 =px.bar(chart_df,x='txn_day',y='total_transaction_amount', orientation='v')
    st.write(fig14)
    st.write(f"""- **:green[Low transactions size]** are recognized in February 2021 especially during **:green[days of 12th-16th]** which are due to Tet holiday in VietNam""")

    st.write("""
    # 3. Additional Notes:
    ### Dimensions in Customer Analysis:
    We can have more and better insights of our Customer if we get information of:
    - Income
    - CIC status, PBC status
    - Risk index internal/external
    - Location (Zipcode) of Customer
    - Marriage status
    - ...

    ### Activities in SuperBank service:
    We can have more and better insights of our Customer journey and potential if we advance our analysis in:
    - Saving account transactions, size, frequently, period
    - Loan Payment status, loan payment transactions
    - Cash in, Cash out through ATM/branch
    """)
