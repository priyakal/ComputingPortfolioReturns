#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import datetime as dt
import xlrd
from dateutil.relativedelta import *
from pandas.tseries.offsets import *
from scipy import stats

#read data containing the default score, market value, delisting returns, and monthly returns 
#for each firm, year, and month. According to Campbell et. al. (2008) this measure is 
#built with a combination of accounting and market data. The variable name reflects this combination.
us_comp_crsp_sp500=pd.read_stata('~/default_score_data.dta')

#form decile portfolios at the end of june

#keep only end of june values
us_comp_crsp_sp500_june=us_comp_crsp_sp500[us_comp_crsp_sp500['month']==6]
us_comp_crsp_sp500_june=us_comp_crsp_sp500_june.sort_values(['year'])
us_comp_crsp_sp500_june['decile']=1+us_comp_crsp_sp500_june.groupby('year')['ind_var'].transform(lambda x:pd.qcut(x,10,labels=False))
us_comp_crsp_sp500_june.sort_values(by=['permno','year'])

#merge with return data 

#portfolio returns have to be calculated from july to june. so merge portfolio assignments with july data
us_port_data=pd.merge(us_comp_crsp_sp500,us_comp_crsp_sp500_june[['permno','year','decile']],on=['permno','year'], how='left')
us_port_data.sort_values(by=['permno','year','month']).set_index(['permno','year','month'],inplace=True)
us_port_data['upd_port']=us_port_data['decile'].shift(6)
us_port_data[['permno','year','month','decile','upd_port']]

#compute monthly EW, VW returns

#lag me for VW returns
us_port_data['me_w_lag']=us_port_data['me_w'].shift(1)

#EW
us_port_data_ew_ret = us_port_data.groupby(['upd_port','year','month'])['retadj_w'].mean().reset_index().rename(columns={'retadj_w':'ewret'})
us_port_data_ew_ret

#VW
def wavg(group, avg_name, weight_name):
    d = group[avg_name]
    w = group[weight_name]
    try:
        return (d * w).sum() / w.sum()
    except ZeroDivisionError:
        return np.nan

us_port_data_vw_ret=us_port_data.groupby(['upd_port','year','month']).apply(wavg, 'retadj_w','me_w_lag').to_frame().reset_index().rename(columns={0: 'vwret'})
us_port_data_vw_ret


#construct arbitrage portfolio
# Transpose portfolio layout to have columns as portfolio returns
#index can only be one value
us_port_data_ew_ret['ym']=us_port_data_ew_ret['year']*100+us_port_data_ew_ret['month']
us_port_data_ew_ret2=us_port_data_ew_ret[['ym','upd_port','ewret']]
ewretdat2 = us_port_data_ew_ret2.pivot(index='ym', columns='upd_port', values='ewret')

us_port_data_vw_ret['ym']=us_port_data_vw_ret['year']*100+us_port_data_ew_ret['month']
us_port_data_vw_ret2=us_port_data_vw_ret[['ym','upd_port','vwret']]
vwretdat2 = us_port_data_vw_ret2.pivot(index='ym', columns='upd_port', values='vwret')

# Add prefix port in front of each column
ewretdat2 = ewretdat2.add_prefix('port')
vwretdat2 = vwretdat2.add_prefix('port')
ewretdat2 = ewretdat2.rename(columns={'port1.0':'lowdefault', 'port10.0':'highdefault'})
vwretdat2 = vwretdat2.rename(columns={'port1.0':'lowdefault', 'port10.0':'highdefault'})
vwretdat2

ewretdat2['high_low'] = ewretdat2['highdefault'] - ewretdat2['lowdefault']
vwretdat2['high_low'] = vwretdat2['highdefault'] - vwretdat2['lowdefault']

#portfolio summary statistics
def_mean_ew = ewretdat2[['highdefault', 'lowdefault', 'high_low']].mean().to_frame()
def_mean_ew = def_mean_ew.rename(columns={0:'mean_ew'}).reset_index()
def_mean_vw = vwretdat2[['highdefault', 'lowdefault', 'high_low']].mean().to_frame()
def_mean_vw = def_mean_vw.rename(columns={0:'mean_vw'}).reset_index()

print(def_mean_ew,def_mean_vw)

# T-Value and P-Value
t_lowdefault_ew = pd.Series(stats.ttest_1samp(ewretdat2['lowdefault'],0.0)).to_frame().T
t_highdefault_ew = pd.Series(stats.ttest_1samp(ewretdat2['highdefault'],0.0)).to_frame().T
t_high_low_ew= pd.Series(stats.ttest_1samp(ewretdat2['high_low'],0.0)).to_frame().T

# T-Value and P-Value
t_lowdefault_vw = pd.Series(stats.ttest_1samp(vwretdat2['lowdefault'],0.0)).to_frame().T
t_highdefault_vw = pd.Series(stats.ttest_1samp(vwretdat2['highdefault'],0.0)).to_frame().T
t_high_low_vw= pd.Series(stats.ttest_1samp(vwretdat2['high_low'],0.0)).to_frame().T

# Compute Long-Short Portfolio Cumulative Returns
ewretdat3 = ewretdat2
ewretdat3['1+lowdefault']=1+ewretdat3['lowdefault']
ewretdat3['1+highdefault']=1+ewretdat3['highdefault']
ewretdat3['1+hl'] = 1+ewretdat3['high_low']

ewretdat3['cumret_lowdefault']=ewretdat3['1+lowdefault'].cumprod()-1
ewretdat3['cumret_highdefault']=ewretdat3['1+highdefault'].cumprod()-1
ewretdat3['cumret_high_low']=ewretdat3['1+hl'].cumprod()-1

import matplotlib.pyplot as plt
plt.plot(ewretdat3['cumret_high_low'])
print(plt.show())

t_lowdefault_ew['momr']='losers'
t_highdefault_ew['momr']='winners'
t_high_low_ew['momr']='long_short'

t_output =pd.concat([t_winners, t_losers, t_long_short])    .rename(columns={0:'t-stat', 1:'p-value'})

# Combine mean, t and p
mom_output = pd.merge(mom_mean, t_output, on=['momr'], how='inner')

