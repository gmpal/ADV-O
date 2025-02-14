import random 
import numpy as np 
import pandas as pd
import pickle
from .customers import *
from .terminals import *
from .transactions import *
from typing import Tuple



class Generator():
    """
    A class for generating synthetic transactions data.
    
    This class can be used to generate a synthetic transactions dataset for use in
    testing or evaluation of fraud detection systems. The dataset includes information
    about customers, terminals, and the transactions themselves, and can be exported
    in various formats.
    
    Parameters:
        n_customers (int): The number of customers to include in the dataset.
        n_terminals (int): The number of terminals to include in the dataset.
        radius (int): The radius within which a customer can use a terminal.
        nb_days (int): The number of days of transactions to generate.
        start_date (str): The starting date for the transaction period.
        random_state (int): The random seed to use for generating the data.
        max_days_from_compromission (int): The maximum number of days from a terminal's
            compromission to a transaction.
        terminal_profiles_table (pandas.DataFrame): A table containing information about
            each terminal in the dataset.
        customer_profiles_table (pandas.DataFrame): A table containing information about
            each customer in the dataset.
        x_y_terminals (numpy.ndarray): The x-y coordinates of each terminal.
        fraudsters_mean (float): The mean transaction amount for fraudsters.
        fraudsters_var (float): The variance in transaction amount for fraudsters.
    """
    
    def __init__(self, n_customers=50, n_terminals=10, radius=20, nb_days=8, start_date="2018-04-01", random_state = 2, \
        max_days_from_compromission=3, compromission_probability=0.03):

        self.n_customers = n_customers
        self.n_terminals = n_terminals
        self.radius = radius
        self.nb_days = nb_days
        self.start_date = start_date
        self.random_state = random_state
        self.max_days_from_compromission = max_days_from_compromission
        self.compromission_probability = compromission_probability
    
        self._initialize() 

    def _initialize(self):
        """
        Initialize the generator by creating the terminal and customer profiles and
        calculating the available terminals for each customer.
        
        This method is called automatically when the `Generator` class is instantiated,
        and does not need to be called directly.
        
        Returns:
            None
        """
        self.terminal_profiles_table = generate_terminal_profiles_table(self.n_terminals, self.random_state)
        self.customer_profiles_table = generate_customer_profiles_table(self.n_customers, self.random_state)
        self.x_y_terminals = self.terminal_profiles_table[['x_terminal_id', 'y_terminal_id']].values.astype(float)
        self.customer_profiles_table['available_terminals'] = self.customer_profiles_table.apply\
            (lambda x: get_list_terminals_within_radius(x, x_y_terminals=self.x_y_terminals, r=self.radius), axis=1)

        self.fraudsters_mean = np.random.normal(np.mean(self.customer_profiles_table['mean_amount'])) * 0.9
        self.fraudsters_var = np.random.normal(np.mean(self.customer_profiles_table['std_amount'])) * 1.3

    def _generate_transactions_table(self, customer_profile: pd.DataFrame) -> pd.DataFrame:
        """
        This function takes the customer profile and returns a DataFrame of transactions for the customer.

        Args:
        customer_profile (pd.DataFrame): A DataFrame containing the customer profile.

        Returns:
        pd.DataFrame: A DataFrame of transactions for the customer.
        """
        days_from_compromission = 0  # Number of max frauds days
        customer_transactions = []
        random.seed(int(customer_profile['CUSTOMER_ID']))
        # For all days
        for day in range(self.nb_days):
            # Random number of transactions for that day
            nb_tx = np.random.poisson(customer_profile.mean_nb_tx_per_day) + 1  #+1 to avoid 0

            if customer_profile['compromised'] == 1 and len(customer_transactions) > 0 and days_from_compromission < self.max_days_from_compromission:
                customer_transactions = generate_fraudulent_transactions(customer_transactions, nb_tx, customer_profile, day, self.fraudsters_mean, self.fraudsters_var, self.terminal_profiles_table, self.x_y_terminals)
                days_from_compromission += 1

            else:
                customer_transactions = generate_genuine_transactions(customer_transactions, nb_tx, customer_profile, day)
                customer_profile['compromised'] = compromise_user(customer_profile, self.compromission_probability)

        customer_transactions = pd.DataFrame(customer_transactions,
                                             columns=['TX_TIME_SECONDS_INSIDE_DAY', 'TX_TIME_DAYS', 'CUSTOMER_ID',
                                                      'TERMINAL_ID', 'TX_AMOUNT', 'TX_FRAUD'])

        if customer_transactions.shape[0] > 0:
            customer_transactions['TX_TIME_SECONDS'] = customer_transactions["TX_TIME_SECONDS_INSIDE_DAY"] + \
                                                       customer_transactions["TX_TIME_DAYS"] * 86400
            customer_transactions['TX_DATETIME'] = pd.to_datetime(customer_transactions['TX_TIME_SECONDS'], unit='s',
                                                                  origin=self.start_date)
            customer_transactions = customer_transactions[
                ['TX_DATETIME', 'CUSTOMER_ID', 'TERMINAL_ID', 'TX_AMOUNT', 'TX_TIME_SECONDS', 'TX_FRAUD']]

        return customer_transactions

    def generate(self) -> None:
        """Generate the synthetic transactions dataset.

        This function generates the synthetic transactions dataset and stores it in the
        `transactions_df` attribute of this object. This function also stores the terminal
        profiles in the `terminal_profiles_table` attribute of this object.
        """

        groups = self.customer_profiles_table.groupby('CUSTOMER_ID')
        self.transactions_df = groups.apply(lambda x: self._generate_transactions_table(customer_profile=x.iloc[0])).reset_index(drop=True)    

    def export(self, filename: str ='dataset', format: str ='csv', include_frauds: bool =True) -> None:
        """Exports the transactions data to a file.

        This function saves the transactions data stored in the `transactions_df` attribute of 
        this object merged with the terminal profiles stored in the `terminal_profiles_table`
        attribute of this object to a file with the specified `filename` and
        `format`. If `format` is 'csv', the data is saved as a CSV file. If
        `format` is 'pkl', the data is pickled and saved to a binary file.
        If `include_frauds` is True, only the fraudulent transactions are saved
        in a separate file.

        Args:
            filename (str): The name of the file to save the data to.
            format (str): The format to use for saving the data. Must be 'csv' or
                'pkl'.
            include_frauds (bool): Whether to include only the fraudulent transactions
        Returns:
            None
        """
        

        full_transactions_table = self.transactions_df.merge(self.terminal_profiles_table, 'inner')

        #TODO: include customer_profile_table, a disclaimer is needed
        #full_transactions_table = full_transactions_table.merge(self.customer_profiles_table, 'inner')

        filename = filename + '.' + format
        if format=='csv':
            full_transactions_table.to_csv(filename,index=False)
        elif format=='pkl':
            with open(filename, 'wb') as f:
                pickle.dump(full_transactions_table,f)
    
    def load(self, filename='dataset.csv'):
        """Loads data from a file into the TransactionData object.

        The file can be in either CSV or pickle format, as determined by the file extension. If the file extension is not
        recognized, a ValueError will be raised.

        Args:
            filename (str): The name of the file to load the data from. Default is 'dataset.csv'.
        """
        #if filename ends with '.csv' then load csv
        #if filename ends with '.pkl' then load pickle
        #else raise error
        if  filename.endswith('.csv'):
            full_transactions_table = pd.read_csv(filename)
        elif filename.endswith('.pkl'):
            with open(filename, 'rb') as f:
                full_transactions_table = pickle.load(f)
        else:
            raise ValueError('Invalid file format')
        
        self.transactions_df = full_transactions_table[['TX_DATETIME', 'CUSTOMER_ID', 'TERMINAL_ID', 'TX_AMOUNT', 'TX_TIME_SECONDS', 'TX_FRAUD']]
        self.transactions_df = self.transactions_df.drop_duplicates()
        self.transactions_df = self.transactions_df.reset_index(drop=True)
        
        self.terminal_profiles_table = full_transactions_table[['TERMINAL_ID', 'x_terminal_id', 'y_terminal_id']]
        self.terminal_profiles_table = self.terminal_profiles_table.drop_duplicates()
        self.terminal_profiles_table = self.terminal_profiles_table.reset_index(drop=True)
        
        #TODO: include customer_profile_table, a disclaimer is needed
        #self.customer_profiles_table = full_transactions_table[['CUSTOMER_ID', 'x_customer_id', 'y_customer_id', 'mean_amount', 'std_amount', 'mean_nb_tx_per_day', 'compromised','available_terminals']]
        #self.customer_profiles_table = self.customer_profiles_table.drop_duplicates()
        #self.customer_profiles_table = self.customer_profiles_table.reset_index(drop=True)
    
        


# TODO: fix this function, why the conditions? LOC and SCALE as parameters
def compute_first_centre() -> Tuple[float, float]:
    """
    Compute the coordinates of the first center.
    
    Returns
    -------
    Tuple[float, float]
        A tuple containing the x and y coordinates of the first center.
    """
    x, y = np.random.normal(loc=70, scale=4), np.random.normal(loc=20, scale=6)
    while x > 100 or x < 0:
        x = np.random.normal(loc=70, scale=4)
    while y > 100 or y < 0:
        y = np.random.normal(loc=20, scale=4)
    return x, y


def compute_first_time() -> int:
    """
    Compute the first time of transaction.
    
    Returns
    -------
    int
        An integer representing the first time of transaction.
    """
    time_tx = abs(int(np.random.normal(86400 / 8, 20000)))
    return time_tx



def compute_first_amount(fraudsters_mean: float, fraudsters_var: float) -> float:
    """
    Compute the first amount of transaction.
    
    Parameters
    ----------
    fraudsters_mean: float
        The mean amount of transaction for fraudsters.
    fraudsters_var: float
        The variance of the amount of transaction for fraudsters.
    
    Returns
    -------
    float
        A float representing the first amount of transaction.
    """
    first_amount = np.random.normal(loc=fraudsters_mean, scale=fraudsters_var)
    first_amount = np.round(first_amount, decimals=2)
    # print('Amount is' + str(first_amount))
    return first_amount


def compute_new_centre(previous_X: float, previous_Y: float) -> Tuple[float, float]:
    """
    Compute the coordinates of the new center.
    
    Parameters
    ----------
    previous_X: float
        The previous x coordinate of the center.
    previous_Y: float
        The previous y coordinate of the center.
    
    Returns
    -------
    Tuple[float, float]
        A tuple containing the x and y coordinates of the new center.
    """
    small_x = previous_X / 100
    small_y = previous_Y / 100

    X = (small_x * 0.75 - 0.06 * small_y + 0.08 * small_x ** 2 + 0.5 * small_y ** 2 - small_x * small_y * 0.3) * 100
    Y = (small_x * 0.3 + 0.85 * small_y - 0.3 * small_x ** 2 + 0.1 * small_y ** 2 - small_x * small_y * 0.3) * 100

    new_centreX = np.random.normal(loc=X, scale=5)
    new_centreY = np.random.normal(loc=Y, scale=5)

    while new_centreX > 100 or new_centreX < 0:
        # print('+')
        new_centreX = np.random.normal(loc=X, scale=10)
    while new_centreY > 100 or new_centreY < 0:
        new_centreY = np.random.normal(loc=Y, scale=10)
        # print('+')
    return new_centreX, new_centreY


def compute_new_amt(previous_AMT: float, previous_X: float, previous_Y: float, fraudsters_var: float) -> float:
    """
    Compute the new amount of transaction.
    
    Parameters
    ----------
    previous_AMT: float
        The previous amount of transaction.
    previous_X: float
        The previous x coordinate of the center.
    previous_Y: float
        The previous y coordinate of the center.
    fraudsters_var: float
        The variance of the amount of transaction for fraudsters.
    
    Returns
    -------
    float
        A float representing the new amount of transaction.
    """
    value = np.random.normal(1.1 * previous_AMT - 0.2 * previous_X + 0.7 + previous_Y * 0.1, fraudsters_var / 2)
    return np.abs(value)


# TODO. why not separating the computation of the first time from the computation
# of the second time similarly to the other functions? The condition
# if previous_fraud[1] == day is very unclear.

# If first fraud of the day, go random, oterwise take from previous fraud.
def compute_time(previous_fraud: tuple, day: int) -> int:
    """
    Computes the time of a transaction.

    Args:
        previous_fraud (tuple): A tuple containing the previous time of fraud and the day on which it occurred.
        day (int): The current day.

    Returns:
        int: The time of the transaction.
    """
    if previous_fraud[1] == day:  # DAY
        time_tx = int(previous_fraud[0] + abs(np.random.normal(loc=0, scale=30000)))
        while time_tx > 86400:
            time_tx = int(previous_fraud[0] + abs(np.random.normal(loc=0, scale=30000)))
    else:
        time_tx = compute_first_time()
    return time_tx

