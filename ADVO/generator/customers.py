import numpy as np
import pandas as pd 

def generate_customer_profiles_table(n_customers: int, random_state: int = 0) -> pd.DataFrame:
    """
    Generate customer profiles for a given number of customers.
    
    Parameters
    ----------
    n_customers: int
        The number of customers to generate.
    random_state: int, optional
        The random state to use. This is an optional parameter with a default value of 0.
    
    Returns
    -------
    pandas.DataFrame
        A DataFrame containing the generated customer profiles.
    """
    np.random.seed(random_state)
    customer_profiles_table = pd.DataFrame(columns=['CUSTOMER_ID', 'x_customer_id', 'y_customer_id',
                                                    'mean_amount', 'std_amount', 'mean_nb_tx_per_day', 'compromised'])
    # Generate customer properties from random distributions
    for customer_id in range(n_customers):
        x_customer_id = np.random.uniform(0, 100)
        y_customer_id = np.random.uniform(0, 100)
        mean_amount = np.random.uniform(5, 100)  # Arbitrary (but sensible) value
        std_amount = mean_amount / 2  # Arbitrary (but sensible) value
        mean_nb_tx_per_day = np.random.uniform(0, 4)  # Arbitrary (but sensible) value

        compromised = 0
        customer_profiles_table.loc[len(customer_profiles_table)] = [customer_id,
                                       x_customer_id, y_customer_id,
                                       mean_amount, std_amount,
                                       mean_nb_tx_per_day, compromised]

    return customer_profiles_table

