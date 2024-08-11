import os
import json
import zlib
import atexit
import concurrent.futures
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox
from typing import List, Tuple

# ファイル名定義
DATA_FILE = "board_data.json"
COMPRESSED_DATA_FILE = "board_data_compressed.zlib"

def fetch_urls(initial_url: str, prefix: str) -> List[str]:
    try:
        response = requests.get(initial_url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URLs: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    return [link.get("href") for link in soup.find_all("a") if link.get("href", "").startswith(prefix)]

def fetch_content(url: str) -> Tuple[List[str], List[Tuple[str, bool]], List[List[str]], List[List[str]]]:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    list_tags = soup.find_all("li")
    alltextlist = []
    ressnum = []
    allcontentlist = []

    A_T_list = []
    A_H_list = []
    for list_tag in list_tags:
        a_titles_list = []
        a_hrefs_list = []
        part_text = ""
        divs = list_tag.find_all("div")
        if len(divs) > 1:
            spans = divs[0].find_all("span")
            num_str = spans[0].text
            num = int(''.join(filter(str.isdigit, num_str)))
            allcontentlist.append(divs[1].prettify())
            p_tags = divs[1].find_all("p", recursive=False)
            a_tags = divs[1].find_all("a", recursive=True)
            
            for p in p_tags:
                part_text += p.text.strip() + '<br>'
                
            for a in a_tags:
                if 'youtube mvthumb' in a.get("class", []):
                    youtube_url = f"https://www.youtube.com/watch?v={a.get('data', '')}"
                    a_titles_list.append(a.get("title", ""))
                    a_hrefs_list.append(youtube_url)
                else:
                    a_titles_list.append(a.get("title", ""))
                    a_hrefs_list.append(a.get("href", ""))
                    
            alltextlist.append(part_text)
            A_T_list.append(a_titles_list)
            A_H_list.append(a_hrefs_list)
            ressnum.append(num)

    effective_list = [(text, False) if text == "このレスは削除されています" else (text, True) for text in alltextlist]

    return allcontentlist, effective_list, A_H_list, A_T_list

def load_compressed_data() -> Tuple[List[str], List[Tuple[List[str], List[Tuple[str, bool]], List[List[str]], List[List[str]]]]]:
    if os.path.exists(COMPRESSED_DATA_FILE):
        with open(COMPRESSED_DATA_FILE, "rb") as f:
            compressed_data = f.read()
            try:
                decompressed_data = zlib.decompress(compressed_data)
                combined_data = json.loads(decompressed_data.decode('utf-8'))
                return combined_data["links"], combined_data["data"]
            except (json.JSONDecodeError, zlib.error, ValueError) as e:
                print(f"Error loading compressed data: {e}")
    return [], []

def save_compressed_data(links: List[str], data: List[Tuple[List[str], List[Tuple[str, bool]], List[List[str]], List[List[str]]]]) -> None:
    combined_data = {
        "links": links,
        "data": data
    }
    try:
        json_data = json.dumps(combined_data, ensure_ascii=False).encode('utf-8')
        compressed_data = zlib.compress(json_data)
        with open(COMPRESSED_DATA_FILE, "wb") as f:
            f.write(compressed_data)
    except (json.JSONDecodeError, zlib.error, ValueError) as e:
        print(f"Error saving compressed data: {e}")

def fetch_all_content(urls: List[str]) -> List[Tuple[List[str], List[Tuple[str, bool]], List[List[str]], List[List[str]]]]:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(fetch_content, urls))

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

    # ラベルとエントリーウィジェットの作成
    tk.Label(window, text="検索ワード:").pack()
    entry = tk.Entry(window, width=50)
    entry.pack()

    def search_button_click() -> None:
        search_word = entry.get()
        search_word_lst = search_word.split()

        initial_url = "https://writening.net/page?b6huzw"
        prefix = "https://bbs.animanch.com/board/"

        # 保存されたリンク群とデータを読み込む
        saved_links, saved_data = load_compressed_data()

        # 新たに取得したリンク群と比較
        baselinks = fetch_urls(initial_url, prefix)
        if baselinks != saved_links:
            # 新しいリンク群を保存し、データも再取得する
            raw_data = fetch_all_content(baselinks)
            save_compressed_data(baselinks, raw_data)
        else:
            # 保存されたデータを使用
            raw_data = saved_data

        textlist = [x[1] for x in raw_data]
        namelist = [x[2] for x in raw_data]
        titlelist = [x[3] for x in raw_data]

        # 検索を実行
        results = search_keywords(search_word_lst, textlist, namelist, titlelist)

        # 結果をHTMLに変換
        html_results = generate_html_results(baselinks, textlist, results, search_word)
        with open("search_results.html", "w", encoding="utf-8") as f:
            f.write(html_results)

        # 完了メッセージを表示
        messagebox.showinfo("検索完了", "検索が完了しました。結果は 'search_results.html' に保存されています。")

    search_button = tk.Button(window, text="Search", command=search_button_click)
    search_button.pack()

    # ウィンドウを表示
    window.mainloop()

# プログラムの終了時にファイルを保存
atexit.register(lambda: save_compressed_data([], []))

if __name__ == "__main__":
    main()
