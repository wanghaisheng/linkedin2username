from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import aiohttp
import json
import urllib.parse
from dphelper import DPHelper
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
app = FastAPI()

# ... [Constants like BANNER and GEO_REGIONS remain the same]

# The dictionary below contains geo region codes. Because we are limited to 1000 results per search,
# we can use this to batch searches across regions and get more results.
# I found this in some random JS, so who knows if it will change.
# https://static.licdn.com/aero-v1/sc/h/6pw526ylxpzsa7nu7ht18bo8y
GEO_REGIONS = {
    "ar": "100446943",
    "at": "103883259",
    "au": "101452733",
    "be": "100565514",
    "bg": "105333783",
    "ca": "101174742",
    "ch": "106693272",
    "cl": "104621616",
    "de": "101282230",
    "dk": "104514075",
    "es": "105646813",
    "fi": "100456013",
    "fo": "104630756",
    "fr": "105015875",
    "gb": "101165590",
    "gf": "105001561",
    "gp": "104232339",
    "gr": "104677530",
    "gu": "107006862",
    "hr": "104688944",
    "hu": "100288700",
    "is": "105238872",
    "it": "103350119",
    "li": "100878084",
    "lu": "104042105",
    "mq": "103091690",
    "nl": "102890719",
    "no": "103819153",
    "nz": "105490917",
    "pe": "102927786",
    "pl": "105072130",
    "pr": "105245958",
    "pt": "100364837",
    "py": "104065273",
    "re": "104265812",
    "rs": "101855366",
    "ru": "101728296",
    "se": "105117694",
    "sg": "102454443",
    "si": "106137034",
    "tw": "104187078",
    "ua": "102264497",
    "us": "103644278",
    "uy": "100867946",
    "ve": "101490751"
}

class NameMutator():
    """
    This class handles all name mutations.

    Init with a raw name, and then call the individual functions to return a mutation.
    """
    def __init__(self, name):
        self.name = self.clean_name(name)
        self.name = self.split_name(self.name)

    @staticmethod
    def clean_name(name):
        """
        Removes common punctuation.

        LinkedIn users tend to add credentials to their names to look special.
        This function is based on what I have seen in large searches, and attempts
        to remove them.
        """
        # Lower-case everything to make it easier to de-duplicate.
        name = name.lower()

        # Use case for tool is mostly standard English, try to standardize common non-English
        # characters.
        name = re.sub("[àáâãäå]", 'a', name)
        name = re.sub("[èéêë]", 'e', name)
        name = re.sub("[ìíîï]", 'i', name)
        name = re.sub("[òóôõö]", 'o', name)
        name = re.sub("[ùúûü]", 'u', name)
        name = re.sub("[ýÿ]", 'y', name)
        name = re.sub("[ß]", 'ss', name)
        name = re.sub("[ñ]", 'n', name)

        # Get rid of all things in parenthesis. Lots of people put various credentials, etc
        name = re.sub(r'\([^()]*\)', '', name)

        # The lines below basically trash anything weird left over.
        # A lot of users have funny things in their names, like () or ''
        # People like to feel special, I guess.
        allowed_chars = re.compile('[^a-zA-Z -]')
        name = allowed_chars.sub('', name)

        # Next, we get rid of common titles. Thanks ChatGPT for the help.
        titles = ['mr', 'miss', 'mrs', 'phd', 'prof', 'professor', 'md', 'dr', 'mba']
        pattern = "\\b(" + "|".join(titles) + ")\\b"
        name = re.sub(pattern, '', name)

        # The line below tries to consolidate white space between words
        # and get rid of leading/trailing spaces.
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    @staticmethod
    def split_name(name):
        """
        Takes a name (string) and returns a list of individual name-parts (dict).

        Some people have funny names. We assume the most important names are:
        first name, last name, and the name right before the last name (if they have one)
        """
        # Split on spaces and dashes (included repeated)
        parsed = re.split(r'[\s-]+', name)

        # Iterate and remove empty strings
        parsed = [part for part in parsed if part]

        # Discard people without at least a first and last name
        if len(parsed) < 2:
            return None

        if len(parsed) > 2:
            split_name = {'first': parsed[0], 'second': parsed[-2], 'last': parsed[-1]}
        else:
            split_name = {'first': parsed[0], 'second': '', 'last': parsed[-1]}

        # Final sanity check to not proceed without first and last name
        if not split_name['first'] or not split_name['last']:
            return None

        return split_name

    def f_last(self):
        """jsmith"""
        names = set()
        names.add(self.name['first'][0] + self.name['last'])

        if self.name['second']:
            names.add(self.name['first'][0] + self.name['second'])

        return names

    def f_dot_last(self):
        """j.smith"""
        names = set()
        names.add(self.name['first'][0] + '.' + self.name['last'])

        if self.name['second']:
            names.add(self.name['first'][0] + '.' + self.name['second'])

        return names

    def last_f(self):
        """smithj"""
        names = set()
        names.add(self.name['last'] + self.name['first'][0])

        if self.name['second']:
            names.add(self.name['second'] + self.name['first'][0])

        return names

    def first_dot_last(self):
        """john.smith"""
        names = set()
        names.add(self.name['first'] + '.' + self.name['last'])

        if self.name['second']:
            names.add(self.name['first'] + '.' + self.name['second'])

        return names

    def first_l(self):
        """johns"""
        names = set()
        names.add(self.name['first'] + self.name['last'][0])

        if self.name['second']:
            names.add(self.name['first'] + self.name['second'][0])

        return names

    def first(self):
        """john"""
        names = set()
        names.add(self.name['first'])

        return names


class CompanyRequest(BaseModel):
    company: str
    domain: Optional[str] = ""
    depth: Optional[int] = None
    sleep: int = 0
    keywords: Optional[List[str]] = None
    geoblast: bool = False

class Employee(BaseModel):
    full_name: str
    occupation: str

class ScrapingResult(BaseModel):
    company: str
    employees: List[Employee]

async def get_webdriver():
    """
    Try to get a working Selenium browser driver
    """
    browser = DPHelper(browser_path=None, HEADLESS=False)
    return browser

async def login():
    """Creates a new authenticated session."""
    driver = await get_webdriver()

    if driver is None:
        raise HTTPException(status_code=500, detail="Could not find a supported browser for Selenium.")

    driver.get("https://linkedin.com/login")

    # In a real application, you'd need to handle this login process differently
    # For now, we'll just simulate a wait
    await asyncio.sleep(10)  # Simulating user login time

    selenium_cookies = driver.cookies(as_dict=True)
    driver.close()

    session = aiohttp.ClientSession()
    for cookie in selenium_cookies:
        session.cookie_jar.update_cookies({cookie['name']: cookie['value']})

    mobile_agent = ('Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; SCH-I535 '
                    'Build/KOT49H) AppleWebKit/534.30 (KHTML, like Gecko) '
                    'Version/4.0 Mobile Safari/534.30')
    session.headers.update({'User-Agent': mobile_agent,
                            'X-RestLi-Protocol-Version': '2.0.0',
                            'X-Li-Track': '{"clientVersion":"1.13.1665"}'})

    await set_csrf_token(session)

    return session

async def set_csrf_token(session):
    csrf_token = session.cookie_jar.filter_cookies('https://www.linkedin.com')['JSESSIONID'].value.replace('"', '')
    session.headers.update({'Csrf-Token': csrf_token})
    return session

async def get_company_info(name: str, session: aiohttp.ClientSession):
    escaped_name = urllib.parse.quote_plus(name)

    async with session.get(f'https://www.linkedin.com/voyager/api/organization/companies?q=universalName&universalName={escaped_name}') as response:
        if response.status == 404:
            raise HTTPException(status_code=404, detail="Company not found")
        if response.status != 200:
            raise HTTPException(status_code=response.status, detail="Unexpected error when fetching company info")

        text = await response.text()
        if 'mwlite' in text:
            raise HTTPException(status_code=400, detail="LinkedIn 'lite' version not supported")

        try:
            response_json = json.loads(text)
        except json.decoder.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Could not decode JSON when getting company info")

    company = response_json["elements"][0]
    found_id = company['trackingInfo']['objectUrn'].split(':')[-1]
    found_staff = company['staffCount']

    return found_id, found_staff

def set_outer_loops(request: CompanyRequest):
    if request.geoblast:
        return range(0, len(GEO_REGIONS))
    elif request.keywords:
        return range(0, len(request.keywords))
    else:
        return range(0, 1)

def set_inner_loops(staff_count: int, request: CompanyRequest):
    loops = int((staff_count / 50) + 1)
    if request.depth and request.depth < loops:
        return request.depth, request.geoblast
    return loops, request.geoblast

async def get_results(session: aiohttp.ClientSession, company_id: str, page: int, region: str, keyword: str):
    url = ('https://www.linkedin.com/voyager/api/graphql?variables=('
           f'start:{page * 50},'
           f'query:('
           f'{f"keywords:{keyword}," if keyword else ""}'
           'flagshipSearchIntent:SEARCH_SRP,'
           f'queryParameters:List((key:currentCompany,value:List({company_id})),'
           f'{f"(key:geoUrn,value:List({region}))," if region else ""}'
           '(key:resultType,value:List(PEOPLE))'
           '),'
           'includeFiltersInResponse:false'
           '),count:50)'
           '&queryId=voyagerSearchDashClusters.66adc6056cf4138949ca5dcb31bb1749')

    async with session.get(url) as result:
        return await result.text()
def find_employees(result):
    """
    Takes the text response of an HTTP query, converts to JSON, and extracts employee details.

    Returns a list of dictionary items, or False if none found.
    """
    found_employees = []

    try:
        result_json = json.loads(result)
    except json.decoder.JSONDecodeError:
        print("\n[!] Yikes! Could not decode JSON when scraping this loop! :(")
        print("I'm going to bail on scraping names now, but this isn't normal. You should "
              "troubleshoot or open an issue.")
        print("Here's the first 200 characters of the HTTP reply which may help in debugging:\n\n")
        print(result[:200])
        return False

    # Walk the data, being careful to avoid key errors
    data = result_json.get('data', {})
    search_clusters = data.get('searchDashClustersByAll', {})
    elements = paging = search_clusters.get('elements', [])
    paging = search_clusters.get('paging', {})
    total = paging.get('total', 0)

    # If we've ended up with empty dicts or zero results left, bail out
    if total == 0:
        return False

    # The "elements" list is the mini-profile you see when scrolling through a
    # company's employees. It does not have all info on the person, like their
    # entire job history. It only has some basics.
    found_employees = []
    for element in elements:
        # For some reason it's nested
        for item_body in element.get('items', []):
            # Info we want is all under 'entityResult'
            entity = item_body.get('item', {}).get('entityResult', {})

            # There's some useless entries we need to skip over
            if not entity:
                continue

            # There is no first/last name fields anymore so we're taking the full name
            full_name = entity['title']['text'].strip()

            # The name may include extras like "Dr" at the start, so we do some basic stripping
            if full_name[:3] == 'Dr ':
                full_name = full_name[4:]

            # Some users are missing a primary subtitle
            occupation = entity.get('primarySubtitle', {}).get('text', '') if entity.get('primarySubtitle') else ''

            found_employees.append({'full_name': full_name, 'occupation': occupation})

    return found_employees


async def do_loops(session: aiohttp.ClientSession, company_id: str, outer_loops: range, request: CompanyRequest):
    employee_list = []

    for current_loop in outer_loops:
        if request.geoblast:
            region_name, region_id = list(GEO_REGIONS.items())[current_loop]
            current_region = region_id
            current_keyword = ''
        elif request.keywords:
            current_keyword = request.keywords[current_loop]
            current_region = ''
        else:
            current_region = ''
            current_keyword = ''

        for page in range(0, request.depth):
            result = await get_results(session, company_id, page, current_region, current_keyword)

            if "UPSELL_LIMIT" in result:
                break

            found_employees = find_employees(result)

            if not found_employees:
                break

            employee_list.extend(found_employees)

            await asyncio.sleep(request.sleep)

    return employee_list

@app.post("/scrape", response_model=ScrapingResult)
async def scrape_linkedin(request: CompanyRequest, background_tasks: BackgroundTasks):
    async with await login() as session:
        company_id, staff_count = await get_company_info(request.company, session)

        request.depth, request.geoblast = set_inner_loops(staff_count, request)
        outer_loops = set_outer_loops(request)

        employees = await do_loops(session, company_id, outer_loops, request)

    result = ScrapingResult(company=request.company, employees=employees)
    
    # Add background task to write files
    background_tasks.add_task(write_files, request.company, request.domain, employees, "output")

    return result

def write_lines(employees, name_func, domain, outfile):
    """
    Helper function to mutate names and write to an outfile

    Needs to be called with a string variable in name_func that matches the class method
    name in the NameMutator class.
    """
    for employee in employees:
        mutator = NameMutator(employee["full_name"])
        if mutator.name:
            for name in getattr(mutator, name_func)():
                outfile.write(name + domain + '\n')


def write_files(company, domain, employees, out_dir):
    """Writes data to various formatted output files.

    After scraping and processing is complete, this function formats the raw
    names into common username formats and writes them into a directory called
    li2u-output unless specified.

    See in-line comments for decisions made on handling special cases.
    """

    # Check for and create an output directory to store the files.
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Write out all the raw and mutated names to files
    with open(f'{out_dir}/{company}-rawnames.txt', 'w', encoding='utf-8') as outfile:
        for employee in employees:
            outfile.write(employee['full_name'] + '\n')

    with open(f'{out_dir}/{company}-metadata.txt', 'w', encoding='utf-8') as outfile:
        outfile.write('full_name,occupation\n')
        for employee in employees:
            outfile.write(employee['full_name'] + ',' + employee["occupation"] + '\n')

    with open(f'{out_dir}/{company}-flast.txt', 'w', encoding='utf-8') as outfile:
        write_lines(employees, 'f_last', domain, outfile)

    with open(f'{out_dir}/{company}-f.last.txt', 'w', encoding='utf-8') as outfile:
        write_lines(employees, 'f_dot_last', domain, outfile)

    with open(f'{out_dir}/{company}-firstl.txt', 'w', encoding='utf-8') as outfile:
        write_lines(employees, 'first_l', domain, outfile)

    with open(f'{out_dir}/{company}-first.last.txt', 'w', encoding='utf-8') as outfile:
        write_lines(employees, 'first_dot_last', domain, outfile)

    with open(f'{out_dir}/{company}-first.txt', 'w', encoding='utf-8') as outfile:
        write_lines(employees, 'first', domain, outfile)

    with open(f'{out_dir}/{company}-lastf.txt', 'w', encoding='utf-8') as outfile:
        write_lines(employees, 'last_f', domain, outfile)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
