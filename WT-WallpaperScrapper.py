import requests
from bs4 import BeautifulSoup
import hashlib
import os
import sys
import configparser

#Made in french then translated, sorry for french variable names

#Initialisation
#reading config file
conf = configparser.ConfigParser()
conf.read("config.cfg")

resolution = conf.get('config', 'resolution')
langs = conf.get('config', 'langs')
langs = langs.replace(' ', '').replace('"', '').replace("'", '').strip('[]').split('","')
screenshot = conf.get('config', 'screenshot')
devblog = conf.get('config', 'devblog')

print("This tool will download wallpapers from the WarThunder website in a wallpapers folder in the same folder as this tool. The duration will depends on what you want to download and on your bandwidth")
print("To change parameters (ie : what to download), edit the config.cfg file.\n")
print("Curent parameters :")
print("Resolution : ", resolution)
print("Download website(s) : ", langs)
print("Download screenshot : ", screenshot)
print("Download wallpapers from devblogs : ", devblog)

#Creating a wallpapers folder, if already exists but empty continue, else prompt the user to delete it
try :
    os.makedirs('wallpapers/')
    print("Creating a wallpapers folder !")
except :
    if os.listdir('wallpapers/') != [] :
        input("Please delete the wallpapers folder, this tool will create one.\nPress ENTER to exit.")
        sys.exit()
    else :
        pass

input("Press ENTER to confirm")
print("Starting to download wallpapers in the wallpapers folder !")

nombres_images = 0

#Looping through each language the user selected
for lang in langs :
    r = requests.get("https://warthunder.com/") #initiating first connection, used for the while loop
    page = 1

    while r.status_code == 200 :    #looping until it gets a 404 error
        url = "https://warthunder.com/" + lang + "/media/wallpapers/page/" + str(page)
        r = requests.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')

        links = soup.find_all('div', {'class': 'wallpapers__dimensions'})

        image_links = []

        for link in links :
            try :
                #getting every link for images in the page
                image_links.append(link.find('a', {'class': 'wallpapers__dimensions-link gallery galleryScreenshot'}, text = resolution)['href'].replace('//', 'http://'))
            except :
                lost += 1
        #Saving images from the links as temp to reorganise them later
        for i in range(len(image_links)) :
            img_data = requests.get(image_links[i]).content
            with open('wallpapers/wallpaper_' + str(i + nombres_images) + '_temp.jpg', 'wb') as handler:
                handler.write(img_data)

        nombres_images += len(image_links)
        print(str(len(image_links)) + " images were downloaded from " + url)
        page += 1

#screenshots
#Pretty same as above but for the screenshot page which has more or less the same structure
if screenshot :
    nombres_images = 0
    print("Downloading screenshots")
    for lang in langs :
        r = requests.get("https://warthunder.com/")
        page = 1
        while r.status_code == 200 :
            url = "https://warthunder.com/" + lang + "/media/screenshots/page/" + str(page)
            r = requests.get(url)

            soup = BeautifulSoup(r.text, 'html.parser')

            links = soup.find_all('div', {'class': 'wallpapers__image'})

            image_links = []

            for link in links :
                try :
                    image_links.append(link.find('a', {'class': 'gallery galleryMode'})['href'].replace('//', 'http://'))
                except :
                    pass

            for i in range(len(image_links)) :
                img_data = requests.get(image_links[i]).content
                with open('wallpapers/screenshot_' + str(i + nombres_images) + '_temp.jpg', 'wb') as handler:
                    handler.write(img_data)

            nombres_images += len(image_links)
            print(str(len(image_links)) + " images were downloaded from " + url)
            page += 1

#devblogs
#devblog are quite differents as we are getting devblogs links then getting the wallpaper link if it exists and then saving it as temp once again
if devblog :
    nombres_images = 0
    print("Downloading wallpapers from devblogs.")
    r = requests.get("https://warthunder.com/")
    page = 1
    stop = False
    while r.status_code == 200 and stop == False :
        stop = True
        lost = 0

        url = "https://warthunder.com/en/news/page/" + str(page) + "/?tags=Development"
        r = requests.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')

        links = soup.find_all('div', {'class': 'news-item'})

        image_links = []

        for link in links :
            try :
                image_links.append("https://warthunder.com/" + link.find("div", {"class": "news-item__anons"}).find('a', {'class': 'news-item__title'})['href'])
            except :
                pass

        for i in range(len(image_links)) :
            url_page = image_links[i]
            r = requests.get(url_page)
            soup = BeautifulSoup(r.text, 'html.parser')
            try :
                img_link = soup.find("a", text = resolution)["href"]
                if img_link.startswith("http") :    #Some older devblogs have a different file managing structure
                    pass
                else :
                    img_link = "https://static.warthunder.com/" + img_link
                img_data = requests.get(img_link).content
                with open('wallpapers/devblog_' + str(i + nombres_images) + '_temp.jpg', 'wb') as handler:
                    handler.write(img_data)
                stop = False    #If it doesn't find a wallpaper for a whole page, the loop stops because the older devblogs don't have any wallpapers
            except :
                lost += 1   #We need to keep track of "lost" images because some devblogs don't have wallpapers

        nombres_images += len(image_links) - lost
        print(str(len(image_links) - lost) + " images were downloaded from " + url)
        page += 1


file_list = os.listdir('wallpapers/')
print(str(len(file_list)) + " images enregistrées !")

#Download of images is over, we now need to remove doubles
#To check if an image is a double we check the hash of each files, if we find duplicates we remove the first one
duplicates = []
hash_keys = dict()
for index, filename in enumerate(os.listdir('wallpapers/')) :
    if os.path.isfile('wallpapers/' + filename) :
        with open('wallpapers/' + filename, 'rb') as f :
            filehash = hashlib.md5(f.read()).hexdigest()
        if filehash not in hash_keys :
            hash_keys[filehash] = index
        else:
            duplicates.append((index,hash_keys[filehash]))

print("Removing " + str(len(duplicates)) + " doubles !")

for index in duplicates :
    #removing duplicates
    os.remove('wallpapers/' + file_list[index[0]])

print("Reorganising files !")

file_list = os.listdir('wallpapers/')
#We now have an incomplete count (ie : 0 - 1 - 3 - 7 - 8...) and we want an homogeneous one
#We do it first for screenshot by extracting files strating by "screenshot_"
#note : a should be faster by using recursion but performance isn't really that much of a concern here
if screenshot :
    working_file_list = [x for x in file_list if "screenshot_" in x]
    file_max = 0
    for file in working_file_list :
        if int(file.replace("screenshot_", "").replace("_temp.jpg", "")) > file_max :
            file_max = int(file.replace("screenshot_", "").replace("_temp.jpg", ""))

    for i in range(len(working_file_list)) :    #renaming files to fill the gap
        os.rename('wallpapers/' + working_file_list[i], "wallpapers/screenshot_" + str(i) + ".jpg")

#we do the same for devblog images
if devblog :
    working_file_list = [x for x in file_list if "devblog_" in x]
    file_max = 0
    for file in working_file_list :
        if int(file.replace("devblog_", "").replace("_temp.jpg", "")) > file_max :
            file_max = int(file.replace("devblog_", "").replace("_temp.jpg", ""))

    for i in range(len(working_file_list)) :
        os.rename('wallpapers/' + working_file_list[i], "wallpapers/devblog_" + str(i) + ".jpg")

#and now for the regular wallpapers
working_file_list = [x for x in file_list if "wallpaper_" in x]
file_max = 0
for file in working_file_list :
    if int(file.replace("wallpaper_", "").replace("_temp.jpg", "")) > file_max :
        file_max = int(file.replace("wallpaper_", "").replace("_temp.jpg", ""))

for i in range(len(working_file_list)) :
    os.rename('wallpapers/' + working_file_list[i], "wallpapers/wallpaper_" + str(i) + ".jpg")

#Conclusion
print(str(len(os.listdir('wallpapers/'))) + " unique images saved in the wallpapers folder !")
print("Thank you for using this tool made with ♥ by Rudlu")
input("Press ENTER to exit")