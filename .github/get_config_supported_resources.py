import argparse
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import json
import logging
from concurrent import futures
from collections import Counter
import os
import time
import re
import yaml

"""
Summary
This is a simple web scraper to list the resource types supported by AWS Config.

It will write its output to supported_resource_types.yaml -- this should be moved to the rdk subfolder after validating.
"""

# Start with ALL, which is a keyword string used by RDK
all_resources = ["ALL # Special string to support all resource types"]

url = "https://docs.aws.amazon.com/config/latest/developerguide/resource-config-reference.html"
# Start the browser
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Chrome(
    options=chrome_options,
)

# Open the login page
driver.get(url)
driver.implicitly_wait(2)

# Iterate through every h2 header
services = driver.find_elements(By.CLASS_NAME, "table-contents")

# Walk through the table items
for service in services:
    if service.text == "":
        continue
    navigator = service
    try:
        # Find everything with a class of code and get its text
        resources = navigator.find_elements(By.CLASS_NAME, "code")
    except NoSuchElementException:
        logging.info(f"No resources found for {service.text}")
        continue
    if len(resources) == 0:
        logging.info(f"No resources found for {service.text}")
        continue
    # Assert that it matches "AWS::*"
    for resource in resources:
        if re.match(r"AWS::.*", resource.text):
            # Add it to the output list
            all_resources.append(resource.text)
            logging.info(resource.text)

driver.quit()

# Return the output list
yaml_output = {"supported_resources": all_resources}
yaml_output_string = yaml.dump(yaml_output)
with open("supported_resource_types.yaml", "w") as f:
    f.write(yaml_output_string)
