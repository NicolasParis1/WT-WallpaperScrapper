import requests
from bs4 import BeautifulSoup
import os
import sys
import configparser
import re
import concurrent.futures
from tqdm import tqdm
import dhash
from PIL import Image
from time import sleep

#Initialisation
global date
global resolution
global hash_keys
global duplicates
duplicates = []
hash_keys = dict()

#reading config file
conf = configparser.ConfigParser()
conf.read("config.cfg")

resolution = conf.get('config', 'resolution')
langs = conf.get('config', 'langs')
langs = langs.replace(' ', '').replace('"', '').replace("'", '').strip('[]').split(',')
screenshot = conf.get('config', 'screenshot') == "True"
devblog = conf.get('config', 'devblog') == "True"
date = int(conf.get('config', 'date'))
overwriteMode = conf.get('config', 'overwriteMode') == "True"

print("This tool will download wallpapers from the WarThunder website in a wallpapers folder in the same folder as this tool. The duration will depends on what you want to download and on your bandwidth")
print("To change parameters (ie : what to download), edit the config.cfg file.\n")
print("Curent parameters :")
print("Resolution : ", resolution)
print("Download website(s) : ", langs)
print("Download screenshot : ", screenshot)
print("Download wallpapers from devblogs : ", devblog)
print("Will not download images prior to : ", date)

#Creating a wallpapers folder, if already exists but empty continue, else prompt the user to delete it
try :
    os.makedirs('wallpapers/')
    print("Creating a wallpapers folder !")
except :
    if overwriteMode :
        pass
    elif os.listdir('wallpapers/') != [] :
        input("Please delete the wallpapers folder, this tool will create one.\nPress ENTER to exit.")
        sys.exit()
    else :
        pass

input("Press ENTER to confirm")
print("\nSearching wallpapers")

def download(url, img_number, pbar, img_type) :
    global date
    if img_type == "wallpaper" :
        filename = 'wallpapers/wallpaper_' + str(img_number) + '_temp.jpg'
    elif img_type == "screenshot" :
        filename = 'wallpapers/screenshot_' + str(img_number) + '_temp.jpg'
    else :
        filename = 'wallpapers/devblog_' + str(img_number) + '_temp.jpg'
    r = requests.get(url, stream = True)
    x = re.compile(r"\d\d\d\d")  #to extract the date
    if int(x.findall(r.headers['Last-Modified'])[0]) >= date :  #download only if it's recent enough
        img_data = r.content
        with open(filename, 'wb') as handler:
            handler.write(img_data)
        pbar.update(approx_file_size)
    else :
        pbar.total -= approx_file_size
        pbar.refresh()

def removeDoubles() :
    #To check if an image is a double we check the hash of each files, if we find duplicates we remove the first one
    #We use dhash and not just hash to remove duplicates pictures with different logos
    global duplicates
    file_list = os.listdir('wallpapers/')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        pbar = tqdm(total=len(file_list), unit='images')
        for i in range(0, len(file_list), 10) :  #working 10 files at a time
            workinglist = file_list[i:i+10]
            executor.submit(hashThreaded, workinglist, pbar)
    pbar.close()

    print("Removing " + str(len(duplicates)) + " doubles !")
    for index in duplicates :
        #removing duplicates
        os.remove('wallpapers/' + index[0])

def hashThreaded(workinglist, pbar) :
    global hash_keys
    global duplicates
    for index, filename in enumerate(workinglist) :
        if os.path.isfile('wallpapers/' + filename) :
            try :
                image = Image.open('wallpapers/' + filename)    #try to open the image, if it fails, delete it
                row, col = dhash.dhash_row_col(image)
                filehash = dhash.format_hex(row, col)
                if filehash not in hash_keys :
                    hash_keys[filehash] = index
                else:
                    duplicates.append((filename,hash_keys[filehash]))
            except :
                os.remove('wallpapers/' + filename)
            pbar.update(1)

def getWallpapers(page, lang) :
    sublist=[]
    url = "https://warthunder.com/" + lang + "/media/wallpapers/page/" + str(page)
    r = requests.get(url, stream = True)
    if r.status_code != 200 :
        return []

    soup = BeautifulSoup(r.text, 'html.parser')

    links = soup.find_all('div', {'class': 'wallpapers__dimensions'})

    image_links = []

    for link in links :
        try :
            #getting every link for images in the page
            image_links.append(link.find('a', {'class': 'wallpapers__dimensions-link gallery galleryScreenshot'}, text = resolution)['href'].replace('//', 'http://'))
        except :
            pass
    for i in range(len(image_links)) :
        img_link = image_links[i]
        sublist.append(img_link)

    if len(image_links) != 0 :
        print(f"{len(image_links)} more images were found from {url} for a total of {str(len(masterlist))} images\r", end="")
    return sublist

masterlist = []

#Looping through each language the user selected
for lang in langs :
    page = 1
    stop = False

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor :
        while stop == False :    #looping until it gets a 404 error
            thread1 = executor.submit(getWallpapers, page, lang)
            page += 1
            thread2 = executor.submit(getWallpapers, page, lang)
            page += 1
            thread3 = executor.submit(getWallpapers, page, lang)
            page += 1
            thread4 = executor.submit(getWallpapers, page, lang)
            page += 1
            masterlist.extend(thread1.result())
            masterlist.extend(thread2.result())
            masterlist.extend(thread3.result())
            masterlist.extend(thread4.result())
            if thread4.result() == [] :
                stop = True


approx_file_size = 750000 #in byte, estimated
approx_file_size_total = len(masterlist)*approx_file_size
print("\nChecking " + str(len(masterlist)) + " images")

#Starting download
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
    pbar = tqdm(total=approx_file_size_total, unit='B', unit_scale=True)
    for img_number, img_link in enumerate(masterlist) :
        executor.submit(download, img_link, img_number, pbar, "wallpaper")
pbar.close()
print("Downloaded " + str(len(os.listdir('wallpapers/'))) + " images so far")

#screenshots
def getScreenshots(page, lang) :
    sublist=[]
    url = "https://warthunder.com/" + lang + "/media/screenshots/page/" + str(page)
    r = requests.get(url, stream = True)
    if r.status_code != 200 :
        return []

    soup = BeautifulSoup(r.text, 'html.parser')

    links = soup.find_all('div', {'class': 'wallpapers__image'})

    image_links = []

    for link in links :
        try :
            #getting every link for images in the page
            image_links.append(link.find('a', {'class': 'gallery galleryMode'})['href'].replace('//', 'http://'))
        except :
            pass
    for i in range(len(image_links)) :
        img_link = image_links[i]
        sublist.append(img_link)

    if len(image_links) != 0 :
        print(f"{len(image_links)} more images were found from {url} for a total of {str(len(masterlist))} images\r", end="")
    return sublist

#Pretty same as above but for the screenshot page which has more or less the same structure
if screenshot :
    masterlist = []
    print("\nSearching screenshots")
    for lang in langs :
        page = 1
        stop = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor :
            while stop == False :    #looping until it gets a 404 error
                thread1 = executor.submit(getScreenshots, page, lang)
                page += 1
                thread2 = executor.submit(getScreenshots, page, lang)
                page += 1
                thread3 = executor.submit(getScreenshots, page, lang)
                page += 1
                thread4 = executor.submit(getScreenshots, page, lang)
                page += 1
                masterlist.extend(thread1.result())
                masterlist.extend(thread2.result())
                masterlist.extend(thread3.result())
                masterlist.extend(thread4.result())
                if thread4.result() == [] :
                    stop = True

    approx_file_size_total = len(masterlist)*approx_file_size
    print("\nChecking " + str(len(masterlist)) + " images")

    #Starting download
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        pbar = tqdm(total=approx_file_size_total, unit='B', unit_scale=True)
        for img_number, img_link in enumerate(masterlist) :
            executor.submit(download, img_link, img_number, pbar, "screenshot")
    pbar.close()
    print("Downloaded " + str(len(os.listdir('wallpapers/'))) + " images so far")

#devblogs
#devblog are quite differents as we are getting devblogs links then getting the wallpaper link if it exists and then saving it as temp once again
def getDevblog(page) :
    global resolution
    global date
    sublist=[]
    url = "https://warthunder.com/en/news/page/" + str(page) + "/?tags=Development"
    r = requests.get(url, stream = True)
    if r.status_code != 200 :
        return []

    soup = BeautifulSoup(r.text, 'html.parser')

    links = soup.find_all('div', {'class': 'news-item'})

    image_links = []

    for link in links :
        try :
            #getting every link for images in the page
            image_links.append("https://warthunder.com" + link.find("div", {"class": "news-item__anons"}).find('a', {'class': 'news-item__title'})['href'])
        except :
            pass
    for i in range(len(image_links)) :
        url_page = image_links[i]
        r = requests.get(url_page, stream = True)
        if r.status_code == 429 :
            sleep(1)
            continue
        x = re.compile(r"\d\d\d\d")  #to extract the date
        if int(x.findall(r.headers['Last-Modified'])[0]) >= date :  #To avoid looking up older devblogs but it's pretty unreliable
            soup = BeautifulSoup(r.text, 'html.parser')
            try :
                img_link = soup.find("a", text = resolution)["href"]
                if img_link.startswith("http") :    #Some older devblogs have a different file managing structure
                    pass
                else :
                    img_link = "https://static.warthunder.com/" + img_link
                sublist.append(img_link)
            except :
                pass
        sleep(0.5) #to avoid status code 429
    if sublist != [] :
        print(f"{len(sublist)} more images were found from {url} for a total of {str(len(masterlist))} images\r", end="")
    return sublist

if devblog :
    masterlist = []
    nombres_images = 0
    print("Searching wallpapers from devblogs.")
    page = 1
    stop = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor :
        while stop == False :    #looping until it gets a 404 error
            thread1 = executor.submit(getDevblog, page)
            page += 1
            thread2 = executor.submit(getDevblog, page)
            page += 1
            thread3 = executor.submit(getDevblog, page)
            page += 1
            thread4 = executor.submit(getDevblog, page)
            page += 1
            masterlist.extend(thread1.result())
            masterlist.extend(thread2.result())
            masterlist.extend(thread3.result())
            masterlist.extend(thread4.result())
            if thread4.result() == [] :
                stop = True

    approx_file_size_total = len(masterlist)*approx_file_size
    print("\nChecking " + str(len(masterlist)) + " images")

    #Starting download
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        pbar = tqdm(total=approx_file_size_total, unit='B', unit_scale=True)
        for img_number, img_link in enumerate(masterlist) :
            executor.submit(download, img_link, img_number, pbar, "devblog")
    pbar.close()
print("Downloaded " + str(len(os.listdir('wallpapers/'))) + " images so far")

print("Cleaning up")
removeDoubles()
print("Reorganising files")

file_list = os.listdir('wallpapers/')
#We now have an incomplete count (ie : 0 - 1 - 3 - 7 - 8...) and we want an homogeneous one
#We do it first for screenshot by extracting files strating by "screenshot_"
#note : a should be faster by using recursion but performance isn't really that much of a concern here
filetypes = ["wallpaper_"]
if screenshot :
    filetypes.append("screenshot_")
if devblog :
    filetypes.append("devblog_")

for filetype in filetypes :
    working_file_list = [x for x in file_list if filetype in x]
    file_max = 0
    for file in working_file_list :
        if int(file.replace(filetype, "").replace("_temp", "").replace(".jpg", "")) > file_max :
            file_max = int(file.replace(filetype, "").replace("_temp", "").replace(".jpg", ""))

    for i in range(len(working_file_list)) :    #renaming files to fill the gap
        os.replace('wallpapers/' + working_file_list[i], "wallpapers/" + filetype + str(i) + ".jpg")

#Conclusion
print(str(len(os.listdir('wallpapers/'))) + " unique images saved in the wallpapers folder !")
print("Thank you for using this tool made with ♥ by Rudlu")
input("Press ENTER to exit")