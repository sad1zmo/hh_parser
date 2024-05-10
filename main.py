from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests
from urllib.parse import urljoin
from itertools import count
from time import sleep
from terminaltables import SingleTable
from environs import Env

# secret_key = ('v3.r.122070222.d26c71f14231fc9fdf8d7d0eb3c95fa885b39c63.'
#               'b52909c3ef3c40f451b3349418a54726b848daa7')

HH_MOSCOW_AREA_ID = 1
SJ_MOSCOW_AREA_ID = 4
HH_API_URL = 'https://api.hh.ru/'
SJ_API_URL = 'https://api.superjob.ru/2.0/'
TOP_LANGUAGE_VACANCIES = ['JavaScript', 'JAVA', 'Python',
                          'Ruby', 'PHP', 'C++', 'C#']


def get_month_ago_date():
    """
    Get the date of the previous month in the format 'YYYY-MM-DD'.
    """
    today = datetime.now()
    month_ago = today - relativedelta(months=1)
    return month_ago.strftime('%Y-%m-%d')


def get_count_language_vacancies(language, site, secret_key=None):
    """
    Get the count of language vacancies for a given site.

    Parameters:
    - language (str): The programming language to filter the vacancies by.
    - site (str): The site to retrieve the vacancies from. Valid options are 'hh' and 'sj'.

    Returns:
    - int: The count of language vacancies for the specified site.
    """
    if site == 'hh':
        hh_vacancies = get_hh_vacancies(language)
        return len(hh_vacancies)
    if site == 'sj':
        sj_vacancies = get_sj_vacancies(secret_key, language)
        return len(sj_vacancies)


def get_hh_vacancies(language):
    """
    Retrieves a list of vacancies from HeadHunter API based on the provided language.

    Parameters:
    - language (str): The programming language to filter the vacancies by.

    Returns:
    - list: A list of vacancy objects retrieved from the HeadHunter API.
    """
    vacancies_url = urljoin(HH_API_URL, 'vacancies')
    month_ago = get_month_ago_date()
    vacancies = []
    for page in count(0):
        payload = {
            'text': f'Программист {language}',
            'area': HH_MOSCOW_AREA_ID,
            'date_from': month_ago,
            'only_with_salary': 'true',
            'page': page
            }
        page_response = requests.get(vacancies_url, params=payload)
        page_response.raise_for_status()

        page_payload = page_response.json()
        if page >= page_payload['pages']:
            break
        if page == 5:  # поставил задержку потому что api отваливалось по таймауту из за ограничений
            sleep(10)
        vacancies.extend(page_payload['items'])
    return vacancies


def get_sj_vacancies(secret_key, language):
    """
    Retrieves a list of vacancies from SuperJob API based on the provided language and secret key.

    Parameters:
    - secret_key (str): The secret key used to authenticate the API request.
    - language (str): The programming language to filter the vacancies by.

    Returns:
    - list: A list of vacancy objects retrieved from the SuperJob API.

    This function constructs the URL for the SuperJob API endpoint and makes a GET request to retrieve a list of vacancies.
    The request includes the specified language, the secret key for authentication, and the date of the previous month.
    The function iterates through the pages of the API response and appends the vacancies to the list.
    If there are no more pages, the function returns the list of vacancies.
    """
    vacancies_url = urljoin(SJ_API_URL, 'vacancies')
    month_ago = get_month_ago_date()
    vacancies = []
    headers = {
        'X-Api-App-Id': secret_key
    }
    for page in count(0):
        params = {
            'town': 'Москва',
            'keywords': f'{language} разработчик',
            'date_published_from': month_ago,
            'page': page,
            'count': 40
        }
        page_response = requests.get(
            vacancies_url,
            headers=headers,
            params=params)
        page_response.raise_for_status()
        page_payload = page_response.json()

        if page_payload['objects']:
            vacancies.extend(page_payload['objects'])
        else:
            return vacancies


def gather_languages_statistics_hh(languages):
    """
    Calculate statistics for HeadHunter vacancies based on the provided languages.

    Parameters:
    - languages (list): A list of programming languages to gather statistics for.

    Returns:
    - dict: A dictionary containing statistics for each language including the number of vacancies found, processed, and the average salary.
    """
    language_statistic = {}
    for language in languages:
        hh_vacancies = get_hh_vacancies(language)
        if hh_vacancies:
            count_language_vacancies = get_count_language_vacancies(language,
                                                                    'hh')
            avarage_salary, salary_count = get_average_salary(
                hh_vacancies, 'hh'
                )
            language_statistic[language] = {
                'vacancies_found': count_language_vacancies,
                'vacancies_processed': salary_count,
                'average_salary': avarage_salary
                }
    return language_statistic


def gather_languages_statistics_sj(languages, secret_key):
    """
    Calculate statistics for SuperJob vacancies based on the provided languages.

    Parameters:
    - languages (list): A list of programming languages to gather statistics for.

    Returns:
    - dict: A dictionary containing statistics for each language including the number of vacancies found, processed, and the average salary.
    """
    language_statistic = {}
    for language in languages:
        sj_vacancies = get_sj_vacancies(secret_key, language)
        if sj_vacancies:
            count_language_vacancies = get_count_language_vacancies(language,
                                                                    'sj',
                                                                    secret_key)
            avarage_salary, salary_count = get_average_salary(
                sj_vacancies, 'sj'
                )
            language_statistic[language] = {
                'vacancies_found': count_language_vacancies,
                'vacancies_processed': salary_count,
                'average_salary': avarage_salary
                }
    return language_statistic


def predict_salary(salary_from, salary_to):
    """
    A function that predicts the salary based on salary_from and salary_to parameters.

    Parameters:
    - salary_from (int): The starting salary range.
    - salary_to (int): The ending salary range.

    Returns:
    - int or None: The predicted salary based on the provided salary ranges.
    """
    if salary_from and salary_to:
        return (salary_to - salary_from) // 2 + salary_from
    if salary_from:
        return salary_from * 1.2
    if salary_to:
        return salary_to * 0.8
    return None


def predict_rub_salary_hh(vacancy):
    """
    A function that predicts the salary in Russian Rubles for a certain vacancy on the HeadHunter site.

    Parameters:
    - vacancy (dict): A dictionary containing information about the vacancy.

    Returns:
    - int or None: The predicted salary in Russian Rubles or None if the currency is not 'RUR'.
    """
    salary = vacancy['salary']
    if salary['currency'] == 'RUR':
        return predict_salary(salary.get('from'), salary.get('to'))
    return None


def predict_rub_salary_sj(vacancy):
    """
    A function that predicts the salary in Russian Rubles for a certain vacancy on the Superjob site.

    Parameters:
    - vacancy (dict): A dictionary containing information about the vacancy.

    Returns:
    - int or None: The predicted salary in Russian Rubles or None if the currency is not 'rub'.
    """
    if vacancy['currency'] == 'rub':
        return predict_salary(vacancy.get('payment_from'),
                              vacancy.get('payment_to'))
    return None


def get_average_salary(all_vacancies, site):
    """
    Calculate the average salary and the number of vacancies for a given site.

    Parameters:
    - all_vacancies (list): A list of vacancy dictionaries.
    - site (str): The name of the site for which the average salary is calculated.

    Returns:
    - avarage_salary (int): The average salary calculated from the vacancies.
    - vacancy_count (int): The number of vacancies processed.

    This function iterates over the list of vacancies and calculates the average salary. 
    It checks the site parameter to determine which prediction function to use for calculating the salary.
    If the prediction function returns a value, it increments the vacancy_count and adds the salary to the total.
    If the prediction function returns None, it adds 0 to the average_salary.
    Finally, it calculates the average_salary by dividing the total salary by the vacancy_count.
    The function returns the average_salary and the vacancy_count as a tuple.
    """
    salary = 0
    vacancy_count = 0
    avarage_salary = 0
    for vacancy in all_vacancies:
        if site == 'hh':
            predict_rub_salary = predict_rub_salary_hh(vacancy)
        if site == 'sj':
            predict_rub_salary = predict_rub_salary_sj(vacancy)
        if predict_rub_salary:
            vacancy_count += 1
            salary += predict_rub_salary
        else:
            avarage_salary += 0  # на весь язык во всех вакансиях не указана зп
        if vacancy_count:
            avarage_salary = salary / vacancy_count
    return int(avarage_salary), vacancy_count


def make_vacancies_table(vacancies_statistic, site):
    """
    Generate a table based on the vacancies statistic for a specific site.

    Parameters:
    - vacancies_statistic (dict): A dictionary containing statistics for different programming languages.
    - site (str): The name of the site for which the statistics are generated.

    Returns:
    - str: A formatted table representing the vacancies statistic for the given site.
    """
    title = f'Статистика поиска вакансий на {site}'
    table_data = [['Язык программирования', 'Вакансий найдено',
                   'Вакансий обработано', 'Средняя зарплата']]
    for item in vacancies_statistic:
        table_data.append([
            item,
            vacancies_statistic[item]['vacancies_found'],
            vacancies_statistic[item]['vacancies_processed'],
            vacancies_statistic[item]['average_salary']
        ])

    table_instance = SingleTable(table_data, title)
    table_instance.inner_heading_row_border = False
    table_instance.inner_row_border = True
    table_instance.justify_columns = {0: 'center', 1: 'center', 2: 'center'}
    return table_instance.table


def main():
    env = Env()
    env.read_env()
    sj_secret_key = env.str('SJ_SECRET_KEY')
    print(sj_secret_key)
    print(make_vacancies_table(
        gather_languages_statistics_hh(TOP_LANGUAGE_VACANCIES), 'HH'))
    print()
    print(make_vacancies_table(
        gather_languages_statistics_sj(
            TOP_LANGUAGE_VACANCIES,
            sj_secret_key),
        'SuperJob'))


if __name__ == '__main__':
    main()
