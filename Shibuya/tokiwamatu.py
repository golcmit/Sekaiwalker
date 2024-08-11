import concurrent.futures
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox
from typing import List, Tuple, Dict, Union

# URLを取得する関数
def fetch_urls(initial_url: str, prefix: str) -> List[str]:
    try:
        response = requests.get(initial_url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URLs: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    return [link.get("href") for link in soup.find_all("a") if link.get("href", "").startswith(prefix)]

# コンテンツを取得する関数
def fetch_content(url: str) -> Tuple[List[BeautifulSoup], List[Tuple[str, bool]], List[List[str]], List[List[str]]]:
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching content from {url}: {e}")
        return [], [], [], []

    soup = BeautifulSoup(response.content, "html.parser")
    list_tags = soup.find_all("li")

    all_content, effective_texts, a_title_list, a_href_list = [], [], [], []
    
    for tag in list_tags:
        divs = tag.find_all("div")
        if len(divs) > 1:
            num_str = divs[0].find_all("span")[0].text
            num = int(''.join(filter(str.isdigit, num_str)))

            all_content.append(divs[1])
            part_text = "<br>".join(p.text.strip() for p in divs[1].find_all("p", recursive=False))
            a_titles = [a.get("title", "") for a in divs[1].find_all("a", recursive=True)]
            a_hrefs = [a.get("href", "") for a in divs[1].find_all("a", recursive=True)]

            all_content.append(divs[1])
            effective_texts.append((part_text, part_text != "このレスは削除されています"))
            a_title_list.append(a_titles)
            a_href_list.append(a_hrefs)

    return all_content, effective_texts, a_href_list, a_title_list

def fetch_all_content(urls: List[str]) -> List[Tuple[List[BeautifulSoup], List[Tuple[str, bool]], List[List[str]], List[List[str]]]]:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(fetch_content, urls))

# 検索結果をHTMLに変換する関数
def generate_html_results(urllist: List[str], textlist: List[List[Tuple[str, bool]]], valuelist: List[Tuple[int, Tuple[int, int]]], searchword: str) -> str:
    if not valuelist:
        return "<html>\n<head>\n</head>\n<body>\n<h1>There seems to be nothing here.</h1>\n</body>\n</html>"

    html_content = f"<html>\n<head>\n</head>\n<body>\n<h1>{len(valuelist)}件見つかりました</h1>\n<h3>検索ワード: {searchword}</h3><ol>\n"
    
    for points, (i, j) in valuelist:
        url = f"{urllist[i]}?res={j + 1}"
        text, _ = textlist[i][j]
        html_content += f"<li><p>{text}</p>\n<a href='{url}'>第{i + 1}スレ{j + 1}レス目</a></li>\n"

    html_content += "</ol>\n</body>\n</html>"
    return html_content

# 検索ワードに基づくスコアリング
def search_keywords(wordlist: List[str], textlist: List[List[Tuple[str, bool]]], namelist: List[List[List[str]]], titlelist: List[List[List[str]]]) -> List[Tuple[int, Tuple[int, int]]]:
    results = []
    
    for i, sublist in enumerate(textlist):
        for j, (text, valid) in enumerate(sublist):
            if not valid:
                results.append((0, (i, j)))
                continue

            score = sum(
                text.count(word) + sum(name.count(word) for name in namelist[i][j]) + sum(title.count(word) for title in titlelist[i][j])
                for word in wordlist
            )
            if score > 0:
                results.append((10 * len(wordlist) * score, (i, j)))

    return [res for res in results if res[0] > 0]

def main() -> None:
    window = tk.Tk()
    window.title("Fate×セカイ検索ツール")

    def search_button_click() -> None:
        initial_url = "https://writening.net/page?b6huzw"
        prefix = "https://bbs.animanch.com/board/"

        search_word = entry.get()
        search_word_lst = search_word.split()

        baselinks = fetch_urls(initial_url, prefix)
        raw_data = fetch_all_content(baselinks)
        textlist = [x[1] for x in raw_data]
        namelist = [x[2] for x in raw_data]
        titlelist = [x[3] for x in raw_data]

        results = search_keywords(search_word_lst, textlist, namelist, titlelist)
        html_content = generate_html_results(baselinks, textlist, results, search_word)

        with open("result.html", "w", encoding='utf-8') as file:
            file.write(html_content)

        messagebox.showinfo('Finished', 'HTML file created successfully.')

    # ウィンドウサイズの設定
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window_width, window_height = 600, 300
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # 入力フレームの作成
    frame = tk.Frame(window)
    frame.pack(pady=20)

    label = tk.Label(frame, text="検索したいワードを入力してください：")
    label.pack()

    entry = tk.Entry(frame, width=60)
    entry.pack()

    button = tk.Button(window, text="検索", command=search_button_click)
    button.pack(pady=10)

    window.mainloop()

if __name__ == '__main__':
    main()
