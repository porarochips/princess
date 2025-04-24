import matplotlib.pyplot as plt
import pandas as pd

plt.style.use('bmh')
#from csv file
df = pd.read_csv('government-finance-statistics-central-government-year-ended-june-2024.csv')
#from excel file
df = df.iloc[:20, 1:]
x = df['STATUS']
y = df['Period']
plt.ylim(2020, 2025)  # Adjust the y-axis range
plt.title('The State Of The Government')
plt.xlabel('StatusOFGovernment', fontsize=18)
plt.ylabel('Period', fontsize=16)
plt.bar(x,y)
plt.show()
 
print(df)