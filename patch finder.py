#!/usr/bin/python3

from itertools import islice
import wget
import mechanicalsoup
import os
from urllib.parse import urljoin, urlsplit
# import sys
# import getopt


def github_issue_patcher(issue_url):
    global browser
    global patch_links
    browser.open(issue_url[2])
    if browser.get_current_page().find('div', {
        "class": "gh-header js-details-container Details js-socket-channel js-updatable-content issue"}).find(
            'span', {"class": "State State--red"}) is not None:
        try:
            issue = browser.get_current_page().find_all("div", {"class": "timeline-commits"})
        except TypeError:
            return
        for commit in issue:
            commit_status = commit.find('div', {"class": "commit-ci-status pr-1"})
            greenlit = commit_status.find('summary', {"class": "text-green"})
            if greenlit is None:
                continue
            else:
                patch_link = urljoin(issue_url[2], commit.find('a', {"class": "commit-id"}).get('href'))
                issue_patch = [issue_url[0], issue_url[1], patch_link + '.diff']
                patch_links.append(tuple(issue_patch))
    return


def dot_git_patcher(issue_url):
    global browser
    global patch_links
    browser.open(issue_url[2])
    page_links = browser.get_current_page().find_all('a')
    for candidate_link in page_links:
        if candidate_link.text == 'patch':
            patch_link = urljoin(issue_url[2], candidate_link.get('href'))
            issue_patch = [issue_url[0], issue_url[1], patch_link]
            patch_links.append(tuple(issue_patch))
        else:
            continue
    return


def gitlab_commit_patcher(commit_url):
    global browser
    global patch_links
    browser.open(commit_url[2])
    if browser.get_current_page().find('a', {"class": "ci-status-icon-success"}) is not None:
        issue_patch = [commit_url[0], commit_url[1], commit_url[2] + '.diff']
        patch_links.append(tuple(issue_patch))
    else:
        pass
    return


def bugzilla_patcher(bug_url):
    global browser
    global patch_links
    browser.open(bug_url[2])
    patch_header_candidate = browser.get_current_page().find_all('h2')
    for header in patch_header_candidate:
        if header.text == 'Patches':
            candidate_patch = header.find_next_sibling().find('a')
            try:
                active_patch_check = candidate_patch.text
            except AttributeError:
                continue
            if active_patch_check != 'Add a Patch':
                patch_link = urljoin(browser.get_url(), candidate_patch.get('href'))
                bug_patch = [bug_url[0], bug_url[1], patch_link]
                patch_links.append(tuple(bug_patch))
                return
    try:
        attachment_check = browser.get_current_page().find('tr', {"class": "bz_contenttype_text_plain bz_patch"})
    except TypeError:
        return
    if attachment_check is not None:
        patch_link = urljoin(browser.get_url(), attachment_check.find('a').get('href'))
        bug_patch = [bug_url[0], bug_url[1], patch_link]
        patch_links.append(tuple(bug_patch))
    return


def download_patches(patches):
    for patch in patches:
        if not (os.path.exists('/tmp/patch-finder/' + str(distribution) + '/' + str(patch[0]) + '/')):
            os.mkdir('/tmp/patch-finder/' + str(distribution) + '/' + str(patch[0]) + '/')
        if patch[2][-6:] == '.patch':
            # print(patch[0] + ' - ' + patch[1][-14:])
            wget.download(patch[2], out='/tmp/patch-finder/' + distribution + '/'
                                        + str(patch[0]) + '/' + patch[1] + ' - ' + patch[2][-9:])
        elif patch[2][-5:] == '.diff':
            # print(patch[0] + ' - ' + patch[1][-13:-5] + '.patch')
            wget.download(patch[2], out='/tmp/patch-finder/' + distribution + '/'
                                        + str(patch[0]) + '/' + patch[1] + ' - ' + patch[2][-13:-5] + '.patch')
        else:
            # print(patch[0] + ' - ' + patch[1][-3:] + '.patch')
            wget.download(patch[2], out='/tmp/patch-finder/' + distribution + '/'
                                        + str(patch[0]) + '/' + patch[1] + ' - ' + patch[2][-3:] + '.patch')
    return


def create_backtrack():
    check_latest_entry = open('/tmp/patch-finder/cve_list', 'r')
    latest_entry = check_latest_entry.readline().split(' ')[0]
    check_latest_entry.close()
    write_latest_entry = open('/tmp/patch-finder/last_cve_entry.txt', 'w')
    write_latest_entry.write(latest_entry)
    write_latest_entry.close()


def check_directories():
    if not (os.path.exists('/tmp/patch-finder/')):
        os.mkdir('/tmp/patch-finder/')
        wget.download(
            'https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/CVE/list',
            out='/tmp/patch-finder/cve_list')
        create_backtrack()

    else:
        if not (os.path.exists('/tmp/patch-finder/cve_list')):
            wget.download(
                'https://salsa.debian.org/security-tracker-team/security-tracker/raw/master/data/CVE/list',
                out='/tmp/patch-finder/cve_list')
            create_backtrack()
    return


check_directories()

cve_entries_to_check = []
possible_cve_entries = []

cve_list = open('/tmp/patch-finder/cve_list', 'r')
reject_entry = ['REJECTED', 'NOT-FOR-US', 'DISPUTED']
recheck_entry = ['RESERVED', 'TODO']
year_vln = str(input("Enter the CVE year to query(1999-2019):\n"))
distribution = str(input("\nEnter the distribution(jessie to sid):\n"))
if not (os.path.exists('/tmp/patch-finder/' + str(distribution) + '/')):
    os.mkdir('/tmp/patch-finder/' + str(distribution) + '/')
query_str = 'CVE-'+year_vln
print("Searching entries matching pattern: " + query_str + " for Debian " + str(distribution))

for line in cve_list:
    if line.startswith(query_str):
        check = ''.join(islice(cve_list, 1))
        if all(flag not in check for flag in reject_entry):
            if any(flag in check for flag in recheck_entry):
                possible_cve_entries.append(str(line.split(' ')[0]))
            else:
                cve_entries_to_check.append(str(line.split(' ')[0]))

if len(possible_cve_entries) != 0:
    future_checks = open('/tmp/patch-finder/pending_checks.txt', 'w')
    for entry in possible_cve_entries:
        future_checks.write(str(entry) + '\n')
    future_checks.close()

vulnerabilities = list(set(cve_entries_to_check))  # remove duplicate cve entries

fixed_from_source = []  # initialize fixed-from-source package list
not_patched = []
patch_links = []
browser = mechanicalsoup.StatefulBrowser()  # initialize browser

for cve in vulnerabilities:
    url = "https://security-tracker.debian.org/tracker/" + cve
    browser.open(url)
    try:
        vulnerability_status = browser.get_current_page().find_all("table")[1]
    except IndexError:
        not_patched.append(cve + ' - ' + 'No info found for CVE entry')
        continue
    package_name = (((vulnerability_status.select('tr')[1]).select('td')[0]).getText()).replace(" (PTS)", "")
    output = 0
    for row in vulnerability_status:
        columns = row.select('td')
        status_entry = []
        for column in columns:
            status_entry.append(column.text)
        if len(status_entry) == 4:
                if distribution in status_entry[1]:
                    '''print("Source package " + source + " (version " + parsed_array[2] + ")" + " is " + parsed_array[3
                    ]+ " (" + entry + ")" + " in " + parsed_array[1])
                    '''
                    if status_entry[3] == 'fixed':
                        fixed_from_source.append(str(package_name) + ' - ' + str(status_entry[2]))
                    else:
                        try:
                            entry_notes = browser.get_current_page().find('pre')
                            noted_links = entry_notes.find_all('a')
                        except (TypeError, AttributeError) as errors:
                            continue
                        for link in noted_links:
                            check_link = urlsplit(link.get('href'))
                            if ('github.com' in check_link[1]) and ('issues' in check_link[2]):

                                candidate_details = [cve, str(package_name) + ' - '
                                                     + status_entry[2], link.get('href')]

                                github_issue_patcher(tuple(candidate_details))

                            elif ('github.com' in check_link[1]) and ('commit' in check_link[2]):

                                candidate_details = [cve, str(package_name) + ' - '
                                                     + status_entry[2], link.get('href') + '.diff']

                                patch_links.append(tuple(candidate_details))

                            elif ('gitlab.' in check_link[1]) and ('commit' in check_link[2]):

                                candidate_details = [cve, str(package_name) + ' - '
                                                     + status_entry[2], link.get('href')]

                                gitlab_commit_patcher(tuple(candidate_details))

                            elif 'git.' in check_link[1][:4]:

                                candidate_details = [cve, str(package_name) + ' - '
                                                     + status_entry[2], link.get('href')]

                                dot_git_patcher(tuple(candidate_details))

                            elif 'bugs.' in check_link[1][:5]:

                                candidate_details = [cve, str(package_name) + ' - '
                                                     + status_entry[2], link.get('href')]

                                bugzilla_patcher(tuple(candidate_details))

                            else:
                                pass
                    output = 1
                else:
                    continue

    if output == 0:
        not_patched.append(package_name + ' - ' + 'No patch found')
        pass

browser.close()
patch_list = list(set(patch_links))  # remove duplicate patches
confirm_download = input("Press any key to start downloading")

download_patches(patch_list)

exit()
