import io
import logging
import os
import smtplib
import time
from typing import Dict, List, Tuple, Callable
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor, Future

import boto3
from scholarly import ProxyGenerator, scholarly, PublicationGenerator


def create_search_query(keyword: str) -> PublicationGenerator:
    """ Constructs Google Scholar search query """
    query = f"""/scholar?q={keyword.strip()}"""
    docker_log.info(f"Constructed query with {query}")
    search_query = scholarly.search_pubs_custom_url(query)
    return search_query


def count(search_query: PublicationGenerator) -> int:
    """ Counts hits in search query. PROBLEM: Google scholar
      will only return 100 pages with 10 items each (1000 items)
    """
    count = 0
    docker_log.info(f"Starting iteration of {search_query}")
    for _ in search_query:
        count = count + 1
        docker_log.info(f"Count {count} Query {search_query}")
        if (count >= THRESHOLD):
            return count
    return count


def count_query_result_number(keyword: str, count_map: Dict[str, int]) -> None:
    """  Count number of articles about keyword k """
    search_query = create_search_query(keyword)
    executed_queries.append(search_query._url)
    print(search_query._url)
    count_map[keyword] = count(search_query)


def get_values_from_bib(
    search_query: PublicationGenerator,
    keyword: str,
    collection: List[Tuple[str, str, str, str, str, str, str]]
) -> None:
    """ Extract values from bibtek """
    i = 0
    for pub in search_query:
        i = i + 1
        if i <= THRESHOLD:
            title = pub.bib['title']
            author = pub.bib['author']
            venue = pub.bib['venue']
            year = pub.bib['year']
            url = "[Not Found]"
            if "url" in pub.bib:
                url = pub.bib['url']
            abstract = "[Not Found]"
            if "abstract" in pub.bib:
                abstract = pub.bib['abstract']

            collection.append(
                (keyword, title, author, venue, year, abstract, url))
        else:
            return


def retrieve_title_and_abstract(
    keyword: str,
    collection: List[Tuple[str, str, str, str, str, str, str]]
) -> None:
    """ Extract title and abstract from bibtek """
    search_query = create_search_query(keyword)
    get_values_from_bib(search_query, keyword, collection)


def initial_search(keywords: List[str]) -> None:
    """ Searches with only one keyword/query """

    print("Queries for initial keywords:")
    countMap = dict()
    futures = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        for k in keywords:
            futures.append(executor.submit(
                count_query_result_number, k=k, cMap=countMap))
    for future in concurrent.futures.as_completed(futures):
        future.result()
    docker_log.info("InitialSearch    : all done")
    print("Baseline count pr keyword:")
    for t in countMap:
        print(t, countMap[t])


def execute_lvl2_keyword_combinations(
    keywords: List[str]
) -> Tuple[List[Future], List[Tuple[str, Dict[str, int]]]]:
    """ Lvl2 search """
    known_searches = []
    results = []
    print("Executed Queries:")
    print()
    futures = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
        ) as executor:
        for k in keywords:
            keyword_combination_results = dict()
            for k2 in keywords:
                if not k == k2:
                    combined = k.strip() + "+" + k2.strip()
                    if not combined in known_searches:
                        known_searches.append(combined)

                        # futures
                        futures.append(executor.submit(
                            count_query_result_number, k=combined,
                            cMap=keyword_combination_results))
            results.append((k, keyword_combination_results))
    docker_log.info(f"lvl2 Created {futures.__len__()} futures")
    return (futures, results)


def execute_lvl3_keyword_combinations(
    keywords: List[str]
) -> Tuple[List[Future], List[Tuple[str, Dict[str, int]]]]:
    """ Lvl3 search """
    futures = []
    known_searches = []
    results = []
    print("Executed Queries:")
    print()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
        ) as executor:
        for k1 in keywords:
            keyword_combination_results = dict()
            for k2 in keywords:
                if not k1 == k2:
                    for k3 in keywords:
                        if not k3 == k2 and not k3 == k1:
                            keys = []
                            keys.append(k1.strip())
                            keys.append(k2.strip())
                            keys.append(k3.strip())
                            keys.sort()
                            combined = keys[0] + "+" + keys[1] + "+" + keys[2]
                            if not combined in known_searches:
                                known_searches.append(combined)
                                futures.append(executor.submit(
                                    count_query_result_number,
                                    k=combined,
                                    cMap=keyword_combination_results))
            results.append((k1, keyword_combination_results))
    docker_log.info(f"lvl3 Created {futures.__len__()} futures")
    return (futures, results)


def print_results_and_create_threads_for_selected_queries(
    input_results: List[Tuple[str, Dict[str, int]]]
) -> Tuple[List[Future], List[Tuple[str, str, str, str, str, str, str]]]:
    """ fetch title and abstract information threaded """
    results = []
    futures = []
    print()
    print("Results for combined keywords")
    print()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
        ) as executor:
        for tup in input_results:
            keyword = tup[0]
            combinedDict = tup[1]
            print("    ", "Combinations with", keyword.strip())
            for key in combinedDict:
                num = combinedDict[key]
                print('        ', key, num)
                futures.append(executor.submit(
                    retrieve_title_and_abstract, k=key, collection=results))
        print()
    return (futures, results)


def convert_list_to_dict(
    results: List[Tuple[str, str, str, str, str, str, str]]
) -> Dict[str, List[Tuple[str, str, str, str, str, str]]]:
    """ Convert list(results) to dict(results_dict) """
    results_dict = dict()
    for e in results:
        (key, title, author, venue, year, abstract, url) = e
        if not key in results_dict:
            results_dict[key] = []
        results_dict[key].append((title, author, venue, year, abstract, url))
    return results_dict


def put_article_information_in_bucket(
    results_dict: Dict[str, List[Tuple[str, str, str, str, str, str]]]
) -> None:
    """ Print selected articles information.
    Captures output and prints as file, and throws file in s3 bucket 
    """
    print()
    for key in results_dict:
        output_path = BASE_PATH+"articles"+'/'
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        f = io.StringIO()
        with redirect_stdout(f):
            print("Showing papers for search query", key)
            for v in results_dict[key]:
                (title, author, venue, year, abstract, url) = v
                print()
                print("    ", "Search term", key)
                print("    ", "Title", title)
                print("    ", "Author", author)
                print("    ", "Venue", venue)
                print("    ", "Year", year)
                print("    ", "Abstract", abstract)
                print("    ", "Url", url)
                print()

        out = f.getvalue()
        print(out)
        output = open(output_path+key+".out", "w")
        output.write(out)
        output.flush()
        output.close()

        s3_resource.Object(AWS_BUCKET_NAME,
                           output_path+key+".out").upload_file(
            Filename=output_path+key+".out")


def combined_search_level_two(keywords: List[str]) -> None:
    """ Combines keywords in tuples, cartesian product """
    (futures, results) = execute_lvl2_keyword_combinations(keywords)
    for future in concurrent.futures.as_completed(futures):
        future.result()

    (futures, results) = print_results_and_create_threads_for_selected_queries(
        results)
    for future in concurrent.futures.as_completed(futures):
        future.result()

    put_article_information_in_bucket(convert_list_to_dict(results))


def combined_search_level_three(keywords: List[str]) -> None:
    """ Combines keywords in triplets, cartesian product """
    (futures, results) = execute_lvl3_keyword_combinations(keywords)
    for future in concurrent.futures.as_completed(futures):
        future.result()

    (futures, results) = print_results_and_create_threads_for_selected_queries(
        results)
    for future in concurrent.futures.as_completed(futures):
        future.result()
    put_article_information_in_bucket(convert_list_to_dict(results))


def extract_keywords() -> List[str]:
    """ load keywords from file """
    docker_log.info("Extracting keywords")
    keywordlistfile = open(FILE, "r")
    keywords = []
    for l in keywordlistfile:
        keywords.append(f""" "{l.replace(' ', '+').strip()}" """)
    keywordlistfile.close()
    return keywords


def create_bucket_if_doesnt_exists() -> None:
    """ create s3 bucket if it doesnt exist """
    try:
        s3_resource.create_bucket(Bucket=AWS_BUCKET_NAME,
                                  CreateBucketConfiguration={
                                      f'LocationConstraint': '{AWS_REGION}'})
        docker_log.info("Bucket created")
    except:
        docker_log.warning("Bucket already exists")


def createa_output_directories() -> None:
    """ creates directory at path if not existing """
    if not os.path.exists(BASE_PATH):
        docker_log.info(f"Creating directory at {BASE_PATH}")
        os.makedirs(BASE_PATH)


def capture_output_as_file_and_upload(function: Callable[[List[str]], None],
                                      output_filename: str,
                                      keywords: List[str],
                                      BASE_PATH: str) -> None:
    """ Executes function and captures output to file, uploads file to S3 """
    docker_log.info(f"Initiating {function} with capture output")
    path = f"{BASE_PATH}{output_filename}"
    f = io.StringIO()
    with redirect_stdout(f):
        function(keywords)
    out = f.getvalue()
    print(out)
    output = open(path, "w")
    output.write(out)
    output.flush()
    output.close()
    docker_log.info(f"Uploading result from {function} to S3 Bucket {path}")
    s3_resource.Object(AWS_BUCKET_NAME, path).upload_file(
        Filename=path)


def send_timings_email(start: float,
                       end_one: float,
                       end_two: float,
                       end_three: float,
                       BASE_PATH: str,
                       inputfilename: str) -> None:
    """ Sends timings mail using GMAIL API """
    bucket_url = "https://%s.s3-%s.amazonaws.com/%s/" % (
        AWS_BUCKET_NAME, AWS_REGION, BASE_PATH)

    analysis_one = end_one - start
    analysis_two = end_two - end_one
    analysis_three = end_three - end_two
    analysis_entire = end_three - start

    port = 465
    smtp_server = "smtp.gmail.com"
    sender_email = os.getenv("GMAIL")
    receiver_email = os.getenv("GMAIL")
    password = os.getenv("GMAIL_PASS")
    message = """\
Subject: Processing of inputfile "{}" is now done.

This message is sent from Python. \n
\n
Level one analysis took {}m\n
Level two analysis took {}m\n
Level three analysis took {}m\n
\n
Elapsed analysis time {}m\n
\n
The result can be found in {}.\n
Please clean up the cloud resources.\n
""".format(inputfilename, int(analysis_one/60), int(analysis_two/60),
           int(analysis_three/60), int(analysis_entire/60), bucket_url)

    docker_log.info(f"Sending mail to {receiver_email}")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)


executed_queries = []
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')
FILE = os.getenv('FILE')
inputfilename = FILE.split('/')[1].split('.')[0]
THRESHOLD = 10
BASE_PATH = f"output/{inputfilename}_{THRESHOLD}/"

s3_resource = boto3.resource(
    's3',
    aws_access_key_id=os.getenv("AWS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET"))

pg = ProxyGenerator()
pg.Tor_External(tor_sock_port=9050, tor_control_port=9051,
                tor_password="scholarly_password")

scholarly.use_proxy(pg)
scholarly.set_retries(500)

MAX_WORKERS = 16

docker_log = logging.getLogger('docker')


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    logging.getLogger('stem').disabled = True
    scholarly_log = logging.getLogger('scholarly')
    docker_log = logging.getLogger('docker')
    docker_log.setLevel(logging.INFO)
    ch = logging.StreamHandler()  #
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    scholarly_log.addHandler(ch)
    docker_log.addHandler(ch)

    docker_log.info("Starting script...")

    keywords = extract_keywords()
    createa_output_directories()
    create_bucket_if_doesnt_exists()

    print("Starting lvl 1")
    start = time.time()
    docker_log.info("Skipping lvl1 search")
    end_one = time.time()

    print("Starting lvl 2")
    docker_log.info("Starting lvl2 search")
    capture_output_as_file_and_upload(
        combined_search_level_two, "lvl2.txt", keywords, BASE_PATH)
    end_two = time.time()

    print("Starting lvl 3")
    docker_log.info("Starting lvl3 search")
    capture_output_as_file_and_upload(
        combined_search_level_three, "lvl3.txt", keywords, BASE_PATH)
    end_three = time.time()

    print("Sending email")
    send_timings_email(start, end_one, end_two, end_three, BASE_PATH)


time.sleep(10)
main()
