import io
import json
import logging
import os
import smtplib
import sys
import threading
import time
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor

import boto3
from scholarly import ProxyGenerator, scholarly


# This script takes 1 argument
#   Argument 1: keywordlist path

# Creates custom query and retrives the iterator from Scholarly
def CreateSearchQuery(keyword):
    """ Constructs Google Scholar search query """
    # Parameters:
    #   hl: eng
    #   lang: eng
    #   as_vis: 0
    #   as_sdt: 0,33
    #   q: keyword
    # try:
    # query = f"""/scholar?hl=en&lr=lang_en&as_vis=0&as_sdt=0,33&q={keyword.strip()}"""
    query = f"""/scholar?q={keyword.strip()}"""
    docker_log.info(f"Constructed query with {query}")
    search_query = scholarly.search_pubs_custom_url(query)
    return search_query
    # except Exception as e:
    #     docker_log.error(e)
    #     CreateSearchQuery(keyword) # retry

# Traverses iterator from Scholarly to count number of articles
def Count(search_query):
    """ Counts hits in search query. PROBLEM: Google scholar will only return 100 pages with 10 items each (1000 items) """
    count = 0
    docker_log.info(f"Starting iteration of {search_query}")
    for _ in search_query:
        count = count + 1
        docker_log.info(f"Count {count} Query {search_query}")
        if(count >= THRESHOLD): return count
    return count

# Thread workload
def CountQueryResultNumber(k, cMap):
    """  Count number of articles about keyword k """
    search_query = CreateSearchQuery(k)
    executed_queries.append(search_query._url)
    print(search_query._url)
    cMap[k] = Count(search_query)

def GetValuesFromBib(search_query, k, collection):
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

            collection.append((k, title, author, venue, year, abstract, url))
        else:
            return

def RetrieveTitleAndAbstract(k, collection):
    """ Extract title and abstract from bibtek """
    search_query = CreateSearchQuery(k)    
    GetValuesFromBib(search_query, k, collection)


# Multithreaded
def InitialSearch(keywords):
    """ Searches with only one keyword/query """

    print("Queries for initial keywords:")
    countMap = dict() # Python collections are threadsafe
    # threads = []
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for k in keywords:
            # docker_log.info("InitialSearch    : before creating thread")
            # t = threading.Thread(target=CountQueryResultNumber, args=(k, countMap), daemon=True)
            # docker_log.info("InitialSearch    : before running thread")
            # t.start()
            # threads.append(t)

            futures.append(executor.submit(CountQueryResultNumber, k=k, cMap=countMap))

    # docker_log.info("InitialSearch    : wait for the thread to finish")
    # for t in threads:
    #     t.join()

    for future in concurrent.futures.as_completed(futures):
        future.result() #side-effect causes values to appear in countMap

    docker_log.info("InitialSearch    : all done")

    print("Baseline count pr keyword:")
    for t in countMap:
        print(t, countMap[t])


def ExecuteLvl2KeywordCombinations(keywords):
    """ Lvl2 search """
    # threads = []
    known_searches = []
    results = []

    print("Executed Queries:")
    print()

    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for k in keywords:
            # for each keyword, try combining with rest of keywords
            keyword_combination_results = dict()
            for k2 in keywords:
                if not k == k2:
                    combined = k.strip() + "+" + k2.strip()

                    # avoid repeat combinations
                    if not combined in known_searches:
                        known_searches.append(combined)

                        # futures
                        futures.append(executor.submit(CountQueryResultNumber, k=combined, cMap=keyword_combination_results))

                        # threads
                        # docker_log.info("ExecuteLvl2KeywordCombinations    : before creating thread")
                        # t = threading.Thread(target=CountQueryResultNumber, args=(combined, keyword_combination_results), daemon=True)
                        # docker_log.info("ExecuteLvl2KeywordCombinations    : before running thread")
                        # t.start()
                        # threads.append(t)


            results.append((k, keyword_combination_results))

    # docker_log.info(f"lvl2 Created {threads.__len__()} threads")
    # return (threads, combined_results)

    docker_log.info(f"lvl2 Created {futures.__len__()} futures")
    return (futures, results)


def ExecuteLvl3KeywordCombinations(keywords):
    """ Lvl3 search """
    # threads = []
    futures = []
    known_searches = []
    results = []

    print("Executed Queries:")
    print()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Check combinations with fewest returns 
        for k1 in keywords:
            # for each keyword, try combining with rest of keywords
            keyword_combination_results = dict()
            for k2 in keywords:
                if not k1 == k2:
                    for k3 in keywords:
                        if not k3 == k2 and not k3 == k1:
                            # above if statements ensure values not euqal and not repeat

                            # sort keywords to avoid repeats when comparing out of order in known combined search strings
                            keys = []
                            keys.append(k1.strip())
                            keys.append(k2.strip())
                            keys.append(k3.strip())
                            keys.sort()

                            combined = keys[0] + "+" + keys[1] + "+" + keys[2]

                            # avoid repeat combinations
                            if not combined in known_searches:
                                known_searches.append(combined)

                                # futures
                                futures.append(executor.submit(CountQueryResultNumber, k=combined, cMap=keyword_combination_results))

                                # docker_log.info("ExecuteLvl3KeywordCombinations    : before creating thread")
                                # t = threading.Thread(target=CountQueryResultNumber, args=(combined, keyword_combination_results), daemon=True)
                                # docker_log.info("ExecuteLvl3KeywordCombinations    : before running thread")
                                # t.start()
                                # threads.append(t)

            results.append((k1, keyword_combination_results))
    
    # docker_log.info(f"lvl3 Created {threads.__len__()} threads")
    # return (threads, results)

    docker_log.info(f"lvl3 Created {futures.__len__()} futures")
    return (futures, results)

def PrintResultsAndCreateThreadsForSelectedQueries(input_results):
    """ fetch title and abstract information threaded """
    results = []
    # threads = []
    futures = []

    print()
    print("Results for combined keywords")
    print()
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for tup in input_results:
            keyword = tup[0]
            combinedDict = tup[1]
            print("    ", "Combinations with", keyword.strip())
            for key in combinedDict:
                num = combinedDict[key]
                print('        ', key, num)
                # if num <= THRESHOLD:
                    # docker_log.info("PrintResultsAndCreateThreadsForSelectedQueries    : before creating thread")
                    # t = threading.Thread(target=RetrieveTitleAndAbstract, args=(key, results), daemon=True)
                    # docker_log.info("PrintResultsAndCreateThreadsForSelectedQueries    : before running thread")
                    # t.start()
                    # threads.append(t)

                futures.append(executor.submit(RetrieveTitleAndAbstract, k=key, collection=results))

        print()

    return (futures, results)
    # return (threads, results)

def ConvertListToDict(results):
    """ Convert list(results) to dict(results_dict) """
    results_dict = dict()
    for e in results:
        (key, title, author, venue, year, abstract, url) = e

        # initialize list before adding elements if first time we see key
        if not key in results_dict:
            results_dict[key] = []

        results_dict[key].append((title, author, venue, year, abstract, url))
    return results_dict

def PutArticleInformationInBucket(results_dict):
    """ Print selected articles information. Captures output and prints as file, and throws file in s3 bucket """
    print()
    for key in results_dict:
        outputPath = BASE_PATH+"articles"+'/'
        if not os.path.exists(outputPath):
            os.makedirs(outputPath)

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
        output = open(outputPath+key+".out", "w")
        output.write(out)
        output.flush()
        output.close()

        s3_resource.Object(AWS_BUCKET_NAME, outputPath+key+".out").upload_file(
            Filename=outputPath+key+".out")


# Check number of articles for each combination of keywords
# Multithreaded
def CombinedSearchLevelTwo(keywords):
    """ Combines keywords in tuples, cartesian product """
    # (threads, results) = ExecuteLvl2KeywordCombinations(keywords)
    # docker_log.info("ExecuteLvl2KeywordCombinations    : wait for the thread to finish")
    # for t in threads:
    #     t.join()

    # (threads, results) = PrintResultsAndCreateThreadsForSelectedQueries(results)
    # docker_log.info("PrintResultsAndCreateThreadsForSelectedQueries    : wait for the thread to finish")
    # for t in threads:
    #     t.join()

    (futures, results) = ExecuteLvl2KeywordCombinations(keywords)
    for future in concurrent.futures.as_completed(futures):
        future.result() #side-effect causes values to appear in results

    (futures, results) = PrintResultsAndCreateThreadsForSelectedQueries(results)
    for future in concurrent.futures.as_completed(futures):
        future.result() #side-effect causes values to appear in results

    PutArticleInformationInBucket(ConvertListToDict(results))

# Check number of articles for combinations of three keywords
# Multithreaded
def CombinedSearchLevelThree(keywords):
    """ Combines keywords in triplets, cartesian product """
    # (threads, results) = ExecuteLvl3KeywordCombinations(keywords)
    # print("Starting threads" , threads.__len__())
    # docker_log.info("ExecuteLvl3KeywordCombinations    : wait for the thread to finish")
    # for t in threads:
    #     t.join()

    # (threads, results) = PrintResultsAndCreateThreadsForSelectedQueries(results)
    # docker_log.info("PrintResultsAndCreateThreadsForSelectedQueries    : wait for the thread to finish")
    # for t in threads:
    #     t.join()

    (futures, results) = ExecuteLvl3KeywordCombinations(keywords)
    for future in concurrent.futures.as_completed(futures):
        future.result() #side-effect causes values to appear in results
    
    (futures, results) = PrintResultsAndCreateThreadsForSelectedQueries(results)
    for future in concurrent.futures.as_completed(futures):
        future.result() #side-effect causes values to appear in results

    PutArticleInformationInBucket(ConvertListToDict(results))

def ExtractKeywords():
    """ load keywords from file """
    docker_log.info("Extracting keywords")
    keywordlistfile = open(FILE, "r")
    keywords = []
    for l in keywordlistfile:
        keywords.append(f""" "{l.replace(' ', '+').strip()}" """)
    keywordlistfile.close()
    # example of resulting collection (from initial.txt)
    # keywords = [
    #     """ "DevOps" """, 
    #     """ "Software+Product+Lines" """,
    #     """ "Regulated+Domain" """,
    #     """ "FDA+Requirement" """,
    #     """ "Continuous+Delivery" """,
    #     """ "Continuous+Integration" """,
    #     """ "Automation+Systems" """,
    #     """ "Software+Validation" """,
    #     """ "Continuous+Software+Engineering" """
    #     ]
    return keywords

def CreateBucketIfDoesntExists():
    """ create s3 bucket if it doesnt exist """
    try: 
        s3_resource.create_bucket(Bucket=AWS_BUCKET_NAME,
                                CreateBucketConfiguration={
                                    f'LocationConstraint': '{AWS_REGION}'})
        docker_log.info("Bucket created")
    except:
        docker_log.warning("Bucket already exists")

def CreateOutputDirectories():
    """ creates directory at path if not existing """
    if not os.path.exists(BASE_PATH):
        docker_log.info(f"Creating directory at {BASE_PATH}")
        os.makedirs(BASE_PATH)

def CaptureOutputAsFileAndUpload(function, outputfilename, keywords, BASE_PATH):
    """ Executes function and captures output to file, uploads file to S3 """
    docker_log.info(f"Initiating {function} with capture output")
    path = f"{BASE_PATH}{outputfilename}"
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

def sendTimingsEmail(start, end_one, end_two, end_three, BASE_PATH):
    """ Sends timings mail using GMAIL API """
    bucket_url = "https://%s.s3-%s.amazonaws.com/%s/" % (AWS_BUCKET_NAME, AWS_REGION, BASE_PATH)
    
    # timeings
    analysis_one = end_one - start
    analysis_two = end_two - end_one
    analysis_three = end_three - end_two
    analysis_entire = end_three - start

    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = os.getenv("GMAIL")  # Enter your address
    receiver_email = os.getenv("GMAIL")  # Enter receiver address
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
""".format(inputfilename, int(analysis_one/60), int(analysis_two/60), int(analysis_three/60), int(analysis_entire/60), bucket_url)

    docker_log.info(f"Sending mail to {receiver_email}")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)


# Program Flow

## VARIABLES
executed_queries = []
AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')
FILE = os.getenv('FILE')
inputfilename = FILE.split('/')[1].split('.')[0]
THRESHOLD = 10
BASE_PATH = f"output/{inputfilename}_{THRESHOLD}/"

s3_resource = boto3.resource(
    's3',
    aws_access_key_id= os.getenv("AWS_KEY_ID"),
    aws_secret_access_key= os.getenv("AWS_SECRET"))

# Setup Scholarly to crawl Scholar with Tor Proxy
pg = ProxyGenerator()
pg.Tor_External(tor_sock_port=9050, tor_control_port=9051, tor_password="scholarly_password")
# pg.SingleProxy(http="127.0.0.1:16379", https="127.0.0.1:16379") # use load balanced tor's 
scholarly.use_proxy(pg)
scholarly.set_retries(500)

MAX_WORKERS=16

docker_log = logging.getLogger('docker')

## MAIN
def main():
    
    # Logging setup
    logging.basicConfig(level=logging.INFO, force=True)
    logging.getLogger('stem').disabled = True
    scholarly_log = logging.getLogger('scholarly')
    docker_log = logging.getLogger('docker')
    docker_log.setLevel(logging.INFO)
    ch = logging.StreamHandler() # create console handler and set level to debug
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') # create formatter
    ch.setFormatter(formatter) # add formatter to ch
    scholarly_log.addHandler(ch) # add ch to logger
    docker_log.addHandler(ch) # add ch to logger

    docker_log.info("Starting script...")

    keywords = ExtractKeywords()
    CreateOutputDirectories()
    CreateBucketIfDoesntExists()

    print("Starting lvl 1")
    # lvl 1 search
    start = time.time()
    docker_log.info("Skipping lvl1 search")
    # docker_log.info("Starting lvl1 search")
    # CaptureOutputAsFileAndUpload(InitialSearch, "lvl1.txt", keywords, BASE_PATH)
    end_one = time.time()

    print("Starting lvl 2")
    # lvl 2 search
    docker_log.info("Starting lvl2 search")
    CaptureOutputAsFileAndUpload(CombinedSearchLevelTwo, "lvl2.txt", keywords, BASE_PATH)
    end_two = time.time()

    print("Starting lvl 3")
    # lvl 3 search
    docker_log.info("Starting lvl3 search")
    CaptureOutputAsFileAndUpload(CombinedSearchLevelThree, "lvl3.txt", keywords, BASE_PATH)
    end_three = time.time()

    print("Sending email")
    # Send report
    sendTimingsEmail(start, end_one, end_two, end_three, BASE_PATH)

    ## END

# print("Waiting for MultiTor")
# time.sleep(120)
time.sleep(10)
main()