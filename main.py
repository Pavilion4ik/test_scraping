import csv
import sys
import logging
from typing import List
from selenium import webdriver
from dataclasses import dataclass, astuple, fields
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait


@dataclass
class Veterinarian:
    name: str
    clinic: str
    reception_time: str
    address: str
    rating: int
    num_reviews: float


class VetParser:
    URL = "https://www.zooplus.de/tierarzt/results?animal_99=true"
    NUM_PAGES = 5
    VETERINARIAN_FIELDS = [field.name for field in fields(Veterinarian)]
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)8s]:  %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler("parser.log")],
    )

    @staticmethod
    def parse_single_veterinarian(page_soup: BeautifulSoup or Tag) -> Veterinarian:
        try:
            clinic = page_soup.select_one(".result-intro__subtitle").text
        except AttributeError:
            clinic = None
        return Veterinarian(
            name=page_soup.select_one(".result-intro__title").text,
            clinic=clinic,
            reception_time=page_soup.select_one(".daily-hours").text,
            address=page_soup.select_one(".result-intro__address").text,
            rating=len(page_soup.select_one(".star-rating ").find_all("span")),
            num_reviews=float(
                page_soup.select_one(".result-intro__rating__note").text.split()[0]
            ),
        )

    def get_single_page_veterinarian(
        self, page_soup: BeautifulSoup
    ) -> List[Veterinarian]:
        veterinarians = page_soup.select(".result-intro__details")
        return [self.parse_single_veterinarian(soup) for soup in veterinarians]

    def get_veterinarians(self, url) -> List[Veterinarian]:
        self.driver.get(url)
        logging.info("Start parsing page #1")
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: d.find_element(By.CLASS_NAME, "result-intro__title")
            )
        finally:
            page = self.driver.page_source
        first_page_soup = BeautifulSoup(page, "lxml")
        veterinarians = self.get_single_page_veterinarian(first_page_soup)
        logging.info("Parsing progress: 20%")
        for page_num in range(2, self.NUM_PAGES + 1):
            logging.info(f"Start parsing page #{page_num}")
            self.driver.get(f"{url}&page={page_num}")
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.find_element(By.CLASS_NAME, "result-intro__title")
                )
            finally:
                page = self.driver.page_source
            soup = BeautifulSoup(page, "lxml")
            veterinarians.extend(self.get_single_page_veterinarian(soup))
            logging.info(f"Parsing progress: {20 * page_num}%")
        return veterinarians

    def write_to_csv(self, veterinarians: [Veterinarian], file_name: str):
        with open(f"{file_name}.csv", "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(self.VETERINARIAN_FIELDS)
            writer.writerows([astuple(veterinarian) for veterinarian in veterinarians])

    def close(self):
        self.driver.close()


def main():
    vet_parser = VetParser()
    veterinarians = vet_parser.get_veterinarians(vet_parser.URL)
    vet_parser.write_to_csv(veterinarians, "veterinarians")
    vet_parser.close()


if __name__ == "__main__":
    main()
