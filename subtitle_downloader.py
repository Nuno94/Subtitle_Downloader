# Script by Nuno Ferreira
# Python script that downloads subtitles for selected file
# Begginer level and tailored to my needs. Just a simple script without the need for many features and using some simple
# console interaction with the user.
# Inspired by:  https://github.com/sameera-madushan/SubtitleBOX
#               https://github.com/manojmj92/subtitle-downloader
#               https://github.com/emericg/OpenSubtitlesDownload


# Subtitle downloader
import hashlib
import os
import pathlib
import requests
import struct
import time
from xmlrpc.client import ServerProxy

# global variables necessary for the login to opensubtitles
os_server = ServerProxy('https://api.opensubtitles.org/xml-rpc')
os_username = ''    # insert username here
os_password = ''    # insert password here


# uses tkinter widget and filedialog to open user window and select the file. Returns the file
def ask_for_file():
    import tkinter
    from tkinter import filedialog
    root = tkinter.Tk()
    root.withdraw()
    file_path = filedialog.askopenfile()
    root.quit()
    return str(file_path.name)


# Returns the file's hash (thesubdb style) (http://thesubdb.com/api/)
def get_file_hash_thesubdb(name):
    readsize = 64 * 1024
    with open(name, 'rb') as f:
        data = f.read(readsize)
        f.seek(-readsize, os.SEEK_END)
        data += f.read(readsize)
    return hashlib.md5(data).hexdigest()


# returns the file's hash (opensubtitles.org style) (https://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes)
def get_file_hash_opensubtitles(name):
    try:

        longlongformat = '<q'  # little-endian long long
        bytesize = struct.calcsize(longlongformat)
        f = open(name, "rb")

        filesize = os.path.getsize(name)
        hash = filesize

        if filesize < 65536 * 2:
            return "SizeError"

        for x in range(int(65536 / bytesize)):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number

        f.seek(max(0, filesize - 65536), 0)
        for x in range(int(65536 / bytesize)):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF

        f.close()
        returnedhash = "%016x" % hash
        return returnedhash

    except(IOError):
        return "IOError"


# Search for subtitles from thesubdb
def search_for_subtitles_subdb(hashed_file):
    # Necessary user-agent. Info at http://thesubdb.com/api/
    # Contains my app. Replace with another one. For tests use http://sandbox.thesubdb.com/
    header = {"user-agent": "SubDB/1.0 (Subtitle_Downloader/1.0; https://github.com/Nuno94/Subtitle_Downloader"}
    search_url = 'http://api.thesubdb.com/?action=search&hash={}'.format(hashed_file)
    req = requests.get(search_url, headers=header)

    if req.status_code == 200:  # OK
        # content returns type bytes. Decoding makes it a string for easy manipulation that I'm used to
        langs_for_file = req.content.decode('utf-8')
        # asks for desired subtitles language to be downloaded
        l = list(langs_for_file.split())
        print('Found these subs on thesubdb:')
        print(l)
        print("\nType language code, type 'open' to search on opensubtitles.org or type 'exit' to close")
        user_selected_lang = input()

        if user_selected_lang.lower() in langs_for_file:
            return user_selected_lang  # will proceed to download

        elif user_selected_lang.lower() == "open":  # will proceed to try opensubtitles.org (method2)
            print("Subdb doesn't have the language you desire. Trying opensubtitles.org")
            return "opensubtitles"

        elif user_selected_lang == "exit":
            return user_selected_lang
        else:
            return print("Selected language error. Probably a typo, try again.")  # Type better next time bruh

    else:  # Will proceed to get from opensubtitles.org (method 2)
        print("Could not get subtitltes for this file from the subdb")
        return "error"


# Donwloads subtitles from subdb
def download_subtittles_from_subdb(hashed_file, language_for_subs, fpath):
    # Necessary user-agent. Info at http://thesubdb.com/api/
    # Contains my app. Replace with another one. For tests use http://sandbox.thesubdb.com/
    header = {"user-agent": "SubDB/1.0 (Subtitle_Downloader/1.0; https://github.com/Nuno94/Subtitle_Downloader"}
    download_url = 'http://api.thesubdb.com/?action=download&hash={}&language={}'.format(hashed_file, language_for_subs)
    req = requests.get(download_url, headers=header)

    if req.status_code == 200:
        # saves the subtiltes with the same name plus the .srt extension (for convenience)
        sub = pathlib.Path(fpath).with_suffix('.srt')
        with open(sub, 'wb') as f:
            f.write(req.content)
        return print("Download successful")
    else:
        return print("Error {}".format(req.status_code))


# Search for subtitles from opensubtitles.org
def search_for_subtitles_from_opensubtitles_by_hash(token, hashed_file, file_size, language_for_subs, saving_path):
    subsearch = os_server.SearchSubtitles(token, [
        {'sublanguageid': language_for_subs, 'moviehash': hashed_file, 'moviebytesize': file_size}])
    cont = 0
    if subsearch['data'] == []:
        print("\nNo subtitltes for that moviehash in those languages. Trying by name")
        # works the path to get the name of the movie cleaner
        temp = saving_path.split('/')
        t = temp[2].split('.')
        i = 1
        q = t[0]
        while i < len(t):
            q = q + ' ' + t[i]
            i += 1
        # serches by the name, gets the id of the movie and then calls the function that will search by the id
        s = os_server.SearchSubtitles(token, [{'query': q}])
        return search_for_subs_opensubtitles_by_name(token, language_for_subs, s['data'][0]['IDMovieImdb'],
                                                     saving_path)

    else:
        # Shows search results by hash and asks for a download or 'name' to perform a different search
        print("\nFound these subs on opensubtitles.org by hash")
        for a in subsearch['data']:
            print("{} {} {}".format(cont, a['LanguageName'], a['SubFileName']))
            cont += 1
        print("\nType number to select subs or type 'name' to go search by name")
        answer = input()
        answer = answer.lower()

        # This option will be used if the hash results don't satisfy me. Then I'll search for more subs using the id
        if answer == 'name':
            return search_for_subs_opensubtitles_by_name(token, language_for_subs, subsearch['data'][0]['IDMovieImdb'],
                                                         saving_path)

        else:
            req = requests.get(subsearch['data'][int(answer)]['SubDownloadLink'])
            sub = pathlib.Path(saving_path).with_suffix('.srt')
            with open(sub, 'wb') as f:
                f.write(req.content)
            return print("Downloaded subs")


# Function name says it's by name, but it will be by id
def search_for_subs_opensubtitles_by_name(token, language_for_subs, movie_id, saving_path):
    moviesearch = os_server.SearchSubtitles(token, [{'sublanguageid': 'eng,por', 'imdbid': movie_id}])
    cont = 0
    # Prints the results and asks for a download
    print("Found these subs on opensubtitles.org by name.")
    for a in moviesearch['data']:
        print("{} {} {}".format(cont, a['LanguageName'], a['SubFileName']))
        cont += 1
    print("\nType number for download or 'exit' to kill.")
    ans = input()
    ans = ans.lower()
    if ans == 'exit':
        return print('Bye')
    else:
        req = requests.get(moviesearch['data'][int(ans)]['SubDownloadLink'])
        sub = pathlib.Path(saving_path).with_suffix('.srt')
        with open(sub, 'wb') as f:
            f.write(req.content)
        return print("Downloaded subs")


def main():
    method = 1
    # Starts by asking to select file. Then proceeds to try thesubdb
    file_path = ask_for_file()
    file_hash_subdb = get_file_hash_thesubdb(file_path)
    lang = search_for_subtitles_subdb(file_hash_subdb)

    # Method of search/download control made by console interaction with user
    if lang == "error" or lang == "opensubtitles":
        method = 2
    elif lang == 'exit':
        print('Bye')
    else:
        download_subtittles_from_subdb(file_hash_subdb, lang, file_path)

    # connects to opensubtitles.org server using user info
    if method == 2:
        try:
            # It's using the name I registered for the app. Replace with another. Same below
            session = os_server.LogIn(os_username, os_password, "eng", 'Subtitle_Downloader_zacarias')
        except Exception:
            time.sleep(0.5)
            try:
                session = os_server.LogIn(os_username, os_password, "eng", 'Subtitle_Downloader_zacarias')
            except Exception:
                print("ERROR: could not connect to opensubtitles.org")
        file_hash_opensubtitles = get_file_hash_opensubtitles(file_path)
        filesize = os.path.getsize(file_path)
        search_for_subtitles_from_opensubtitles_by_hash(session['token'], file_hash_opensubtitles, str(filesize), 'all',
                                                        file_path)


if __name__ == '__main__':
    main()
