#あにまん掲示板 Fate×セカイスレ


import concurrent.futures
import requests
import numpy as np
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox

#rawlist
def fetch_urls(initial_url, prefix):
    response = requests.get(initial_url)
    soup = BeautifulSoup(response.text, "html.parser")

    baselinks = []
    for link in soup.find_all("a"):
        href = link.get("href")
        if href and href.startswith(prefix):
            baselinks.append(href)

    return baselinks

#textlist
def fetch_content(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    list_tags = soup.find_all("li")
    alltextlist = []
    ressnum = []
    allcontentlist = []
   
    A_T_list = []
    A_H_list = []
    for list_tag in list_tags:
        a_titles_list =[]
        a_hrefs_list = []
        part_text = ""
        divs = list_tag.find_all("div")
        if len(divs) > 1:
            spans = divs[0].find_all("span")
            num_str = spans[0].text
            num = ''.join(filter(str.isdigit, num_str))
            allcontentlist.append(divs[1])
            p_tags = divs[1].find_all("p",recursive = False)
            a_tags = divs[1].find_all("a",recursive = True)
            for p in p_tags:
                part_text += p.text.strip() + '<br>'
            for a in a_tags:
                a_titles_list.append(a.get("title", ""))
                a_hrefs_list.append(a.get("href",""))
            alltextlist.append(part_text)
            A_T_list.append(a_titles_list)
            A_H_list.append(a_hrefs_list)
            ressnum.append(int(num))

    effective_list = []
    for text in alltextlist:
        if text == "このレスは削除されています":
            effective_list.append((text, False))
        else:
            effective_list.append((text, True))

    return allcontentlist,effective_list,A_H_list,A_T_list


def fetch_all_content(baselinks):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(fetch_content, baselinks)

    return list(results)

def transform_results(results):
    # Create empty lists for each category
    a_list, b_list, c_list, d_list = [], [], [], []

    for result in results:
        a, b, c, d = result[0], result[1], result[2], result[3]
        a_list.append(a)
        b_list.append(b)
        c_list.append(c)
        d_list.append(d)

    transformed_results = [a_list, b_list, c_list, d_list]
    return transformed_results




#valued_list(Rating sorting is not yet implemented.)
def search_keywords(wordlist,textlist,namelist,titlelist):
    point_list=[]
    for i in range(len(textlist)):
        
        for j in range(len(textlist[i])):
            point_counter = 0
            if textlist[i][j][1] == False:
                point_list.append((0,(i,j)))
            else:
                point_mem = []
                for w in wordlist:
                    name_point = 0
                    title_point =0
                    for k in namelist[i][j]:
                        name_point += k.count(w)
                    for k in titlelist[i][j]:
                        title_point += k.count(w)
                    point_mem.append(textlist[i][j][0].count(w)+name_point+title_point)
                if np.prod(point_mem) != 0:
                    point_counter = 10 * len(wordlist)*sum(point_mem)
                    point_list.append((point_counter,(i,j)))
                else:
                    point_list.append((point_counter,(i,j)))
    filtered_list = [t for t in point_list if t[0] != 0]
    return filtered_list


#htmlfile
def generate_html_results(urllist, textlist, valuelist,searchword):
    if len(valuelist) > 0:
        referencelist = []
        messagelist = []
        stringlist = []
        for i in range(len(valuelist)):
            b = valuelist[i][1][0]
            c = valuelist[i][1][1]
            url = urllist[b] + f"?res={1 + c}"
            referencelist.append(url)
            string = textlist[b][c][0]
            stringlist.append(string)
            messagelist.append(f"第{1 + b}スレ{1 + c}レス目")

        html_content = f"<html>\n<head>\n</head>\n<body>\n<h1>{len(valuelist)}件見つかりました</h1>\n<h3>検索ワード:{searchword}</h3><ol>\n"
        
        for i in range(len(valuelist)):
            html_content += f"<li><p>{stringlist[i]}</p>\n<a href='{referencelist[i]}'>{messagelist[i]}</a></li>\n"
        html_content += "</ol>\n</body>\n</html>"
    else:
        html_content = "<html>\n<head>\n</head>\n<body>\n<h1>There seems to be nothing here.</h1>\n</body>\n</html>"

    return html_content




def main():
    window = tk.Tk()
    window.title("Fate×セカイ検索ツール")

    def search_button_click():
        initial_url = "https://writening.net/page?b6huzw"
        prefix = "https://bbs.animanch.com/board/"

        search_word = word_input()
        search_word_lst = search_word.split()
        #step1
        baselinks = fetch_urls(initial_url, prefix)
        raw_data = transform_results(fetch_all_content(baselinks))
        textlist = raw_data[1]
        addreslist = raw_data[2]
        titlelist = raw_data[3]

        step2 = search_keywords(search_word_lst, textlist,addreslist,titlelist)
        step3 = generate_html_results(baselinks, textlist, step2,search_word)

        with open("result.html", "w",encoding='utf-8') as file:
            file.write(step3)

        messagebox.showinfo('Finished', 'HTML file created successfully.')

    # 画面サイズの取得
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # ウィンドウサイズの設定
    window_width = 600
    window_height = 300

    # ウィンドウを画面中央に配置
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # 入力フレームの作成
    frame = tk.Frame(window)
    frame.pack(pady=20)

    # 入力ラベルの作成
    label = tk.Label(frame, text="検索したいワードを入力してください：")
    label.pack()

    # 入力エントリーの作成
    entry = tk.Entry(frame, width=60)
    entry.pack()

    # ボタンの作成
    button = tk.Button(window, text="検索", command=search_button_click)
    button.pack(pady=10)

    def word_input():
        input_text = entry.get()
        return input_text

    # メインループの開始
    window.mainloop()

if __name__ == '__main__':
    main()
