import os
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import datetime
import csv
import collections
import math
hebrew_alphabet = [chr(letter) for letter in range(0x5d0, 0x5eb)]


def list_from_oddsportal(driver):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    driver.get("http://www.oddsportal.com/matches/soccer/"+tomorrow.strftime('%Y%m%d'))
    driver.find_element_by_id('sort_events').click()
    time.sleep(6)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    containers = soup.find("table", {"class": " table-main"})
    matches = containers.findAll("tr", xeid=True) #("tr", xeid=True)
    links = []
    for match in matches:
        teams = match.findAll("td", {"class": "name table-participant"})
        for a in teams[0].find_all('a', href=True):
            if a['href'] != 'javascript:void(0);':
                teams_split = teams[0].text.split(" - ")
                links.append([teams_split[0].replace(u'\xa0', u''), teams_split[1].replace(u'\xa0', u''), a['href']])
    return links


def get_odds(driver, link):
    driver.get("http://www.oddsportal.com" + link)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    container = soup.find("table", {"class": "table-main detail-odds sortable"})
    odds = container.findAll("tr", {"class": "lo"})
    bookmaker_odds = []
    for odd in odds:
        bookmaker_name = odd.find("a", {"class": "name"}).string
        if bookmaker_name == 'bet365' or bookmaker_name == 'Pinnacle':
            fixed_odds = odd.findAll("td", {"class": ["right odds up", "right odds down", "right odds", "right odds high up", "right odds high down"]})
            if len(fixed_odds) == 3:
                bookmaker_odds.append([bookmaker_name, float(fixed_odds[0].string), float(fixed_odds[1].string), float(fixed_odds[2].string)])
    return bookmaker_odds


def list_from_clubelo(driver):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    driver.get("http://clubelo.com/"+tomorrow.strftime('%Y-%m-%d')+"/Fixtures")
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    containers = soup.findAll("svg")
    table = containers[1].findAll("text", {"fill": "#eee"})
    matches_elo = {}
    sum_matches = 0
    for tab in table:
        if tab.string != None and int(tab['y']) > 70:
            if ((tab.string[0].isupper()) == True) or (tab.string[len(tab.string) - 1] == "%") or (tab.string[0] in hebrew_alphabet):
                if (tab['y'] in matches_elo) == True:
                    matches_elo[tab['y']][tab['x']] = tab.string
                else:
                    sum_matches += 1
                    matches_elo[tab['y']] = {}
                    matches_elo[tab['y']][tab['x']] = tab.string
    print("ClubElo sum of matches = " + str(sum_matches))
    return matches_elo


def read_csv():
    names = []
    with open('names_clubelo_oddsportal.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            names.append(row)
    return names


def is_in_clubelo(clubelo, oddsportal_match, csv):
    temp = 0
    for cs in csv:
        if cs[1] == oddsportal_match[0]:
            home = cs[0]
            temp += 1
        elif cs[1] == oddsportal_match[1]:
            away = cs[0]
            temp += 1
    if temp == 2:
        for key, value in clubelo.items():
            temp_list = list(collections.OrderedDict(sorted(value.items(), key=lambda t: t[0])).items())
            if temp_list[0][1] == home and temp_list[1][1] == away and len(temp_list) > 4: #tutaj najwyżej playoff LM i LE, len(templist) == 5
                del clubelo[key]
                return [True, int(temp_list[2][1].replace(u'%', u'')), int(temp_list[3][1].replace(u'%', u'')), int(temp_list[4][1].replace(u'%', u''))], clubelo
        return [False], clubelo
    else:
        return [False], clubelo


def calculate_odds(oddsportal, clubelo, csv, driver):
    value_bets = []
    links_number = 0
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    for od in oddsportal:
        clubelo_percentage, clubelo = is_in_clubelo(clubelo, od, csv)
        if clubelo_percentage[0]:
            odds_1x2 = get_odds(driver, od[2])
            links_number += 1
            if len(odds_1x2) > 0:
                for odds in odds_1x2:
                    if odds[1]*clubelo_percentage[1]>=101:
                        value_bets.append([tomorrow, tomorrow.month, od[0], od[1], '', '',
                                            '1', str(odds[1]).replace('.',','), math.floor(odds[1]*clubelo_percentage[1]-100), clubelo_percentage[1], odds[0]])
                    if odds[2]*clubelo_percentage[2]>=101:
                        value_bets.append([tomorrow, tomorrow.month, od[0], od[1], '', '',
                                           '0', str(odds[2]).replace('.',','), math.floor(odds[2]*clubelo_percentage[2]-100), clubelo_percentage[2], odds[0]])
                    if odds[3]*clubelo_percentage[3]>=101:
                        value_bets.append([tomorrow, tomorrow.month, od[0], od[1], '', '',
                                           '2', str(odds[3]).replace('.',','), math.floor(odds[3]*clubelo_percentage[3]-100), clubelo_percentage[3], odds[0]])
    print("Visited links = " + str(links_number))
    print(clubelo)
    return value_bets


def write_result_to_csv(result):
    with open('result.csv', 'w', newline='') as file:
        writer = csv.writer(file, delimiter=",")
        for row in result:
            writer.writerow(row)

if __name__ == "__main__":
    chrome_driver = "/Users/Dominik/Desktop/Bet/chromedriver"
    os.environ["webdriver.chrome.driver"] = chrome_driver
    drv = webdriver.Chrome()
    oddsportal_matches = list_from_oddsportal(drv)
    clubelo_matches = list_from_clubelo(drv)
    club_names = read_csv()
    result = calculate_odds(oddsportal_matches, clubelo_matches, club_names, drv)
    write_result_to_csv(result)
    drv.quit()