# -------------------------------
# 1. Imports & Settings
# -------------------------------
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error


# -------------------------------
# 2. Load Data
# -------------------------------
df = pd.read_csv("Nat_Gas.csv")

df['Dates'] = pd.to_datetime(df['Dates'])
df = df.sort_values('Dates')
df.set_index('Dates', inplace=True)

df.rename(columns={'Prices': 'Price'}, inplace=True)

# Feature engineering
df['Year'] = df.index.year
df['Month'] = df.index.month
df['Half'] = np.where(df['Month'] <= 6, 'H1', 'H2')


# -------------------------------
# 3. Rolling Volatility
# -------------------------------
df['Rolling_STD_3M'] = df['Price'].rolling(3).std()
df['Rolling_STD_6M'] = df['Price'].rolling(6).std()
df['Rolling_STD_12M'] = df['Price'].rolling(12).std()


# -------------------------------
# 4. Seasonality (Month-wise)
# -------------------------------
monthly_avg = df.groupby('Month')['Price'].mean()


# -------------------------------
# 5. SARIMA Model
# -------------------------------
train_size = int(len(df) * 0.8)
train = df.iloc[:train_size]
test = df.iloc[train_size:]

model = SARIMAX(
    train['Price'],
    order=(1,1,1),
    seasonal_order=(1,1,1,12)
)
sarima_fit = model.fit()

predicted_prices = sarima_fit.forecast(len(test))

rmse = np.sqrt(mean_squared_error(test['Price'], predicted_prices))
print("Backtesting RMSE:", round(rmse, 3))


# -------------------------------
# 6. Forecast (Next 12 Months)
# -------------------------------
forecast = sarima_fit.forecast(12)

forecast_index = pd.date_range(
    start=df.index.max() + pd.offsets.MonthEnd(1),
    periods=12,
    freq='M'
)

forecast_df = pd.DataFrame(
    {'ForecastPrice': forecast.values},
    index=forecast_index
)


# -------------------------------
# 7. Price Estimation Function
# -------------------------------
def estimate_gas_price_sarima(input_date):
    input_date = pd.to_datetime(input_date)

    if input_date <= df.index.max():
        return round(
            float(
                df['Price']
                .reindex(df.index.union([input_date]))
                .interpolate()
                .loc[input_date]
            ),
            2
        )

    elif input_date <= forecast_df.index.max():
        nearest = input_date.to_period('M').to_timestamp('M')
        return round(float(forecast_df.loc[nearest]), 2)

    else:
        raise ValueError("Forecast available only for next 12 months")


# -------------------------------
# 8. Visual Analytics
# -------------------------------
norm = mcolors.Normalize(vmin=df['Price'].min(), vmax=df['Price'].max())
cmap = plt.cm.Reds

# Price Trend
plt.figure(figsize=(10,5))
plt.scatter(df.index, df['Price'], c=df['Price'], cmap=cmap, norm=norm)
plt.plot(df.index, df['Price'], alpha=0.5)
plt.title("Natural Gas Price Trend")
plt.grid(alpha=0.3)
plt.show()

# Seasonality Line
plt.figure(figsize=(8,4))
plt.bar(monthly_avg.index, monthly_avg.values,
        color=cmap(norm(monthly_avg.values)))
plt.title("Month-wise Seasonality")
plt.show()

# Heatmap
heatmap_data = df.pivot_table(
    values='Price',
    index='Year',
    columns='Month',
    aggfunc='mean'
)

plt.figure(figsize=(12,6))
sns.heatmap(heatmap_data, cmap="Reds", annot=True, fmt=".2f")
plt.title("Price Heatmap (Year vs Month)")
plt.show()

# Volatility
plt.figure(figsize=(12,6))
plt.scatter(df.index, df['Rolling_STD_12M'],
            c=df['Rolling_STD_12M'], cmap=cmap)
plt.plot(df.index, df['Rolling_STD_12M'], alpha=0.5)
plt.title("12M Rolling Volatility")
plt.show()

# Backtesting
plt.figure(figsize=(10,5))
plt.plot(train.index, train['Price'], color='grey', label='Train')
plt.scatter(test.index, test['Price'],
            c=test['Price'], cmap=cmap, label='Actual')
plt.scatter(test.index, predicted_prices,
            c=predicted_prices, cmap=cmap, marker='x', label='Predicted')
plt.legend()
plt.title("SARIMA Backtesting")
plt.show()


# -------------------------------
# 9. Example Outputs
# -------------------------------
print("Estimate (Past):", estimate_gas_price_sarima("2022-07-15"))
print("Estimate (Future):", estimate_gas_price_sarima("2025-02-28"))
