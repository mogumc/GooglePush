import json
import os
import requests
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


def get_existing_urls():
    """
    从urls.json文件中读取已成功提交的URL列表
    """
    json_file = 'urls.json'
    if not os.path.exists(json_file):
        return []
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as e:
        print(f"读取urls.json失败: {e}，将视为空列表处理")
        return []


def save_successful_urls(new_urls):
    """
    将新提交成功的URL追加写入urls.json文件
    """
    json_file = 'urls.json'
    existing_urls = get_existing_urls()
    all_urls = list(set(existing_urls + new_urls))
    
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_urls, f, ensure_ascii=False, indent=4)
        print(f"成功保存 {len(new_urls)} 个URL到 {json_file}")
    except IOError as e:
        print(f"写入urls.json失败: {e}")


def get_urls_from_sitemap(sitemap_url):
    """
    从指定的sitemap.txt链接获取URL列表
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(sitemap_url, headers=headers, timeout=30)
        response.raise_for_status()  # 抛出HTTP错误
        urls = [url.strip() for url in response.text.splitlines() if url.strip()]
        print(f"从 {sitemap_url} 获取到 {len(urls)} 个URL")
        return urls
    except requests.exceptions.RequestException as e:
        print(f"获取sitemap失败: {e}")
        return []


def publish():
    sitemap_url = "https://blog.moguq.top/sitemap.txt"
    all_urls = get_urls_from_sitemap(sitemap_url)
    if not all_urls:
        print("未获取到任何URL，终止提交")
        return []
    
    existing_urls = get_existing_urls()
    urls_to_submit = [url for url in all_urls if url not in existing_urls]
    
    if not urls_to_submit:
        print(f"所有({len(all_urls)} 个)URL都已提交过")
        return []
    
    print(f"本次需要提交的URL数量: {len(urls_to_submit)}")

    successful = []
    requests_dict = {url: "URL_UPDATED" for url in urls_to_submit}
    
    JSON_KEY_FILE = 'key.json'
    SCOPES = ["https://www.googleapis.com/auth/indexing"]
    
    try:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scopes=SCOPES)
        service = build('indexing', 'v3', credentials=credentials)
        
        def index_api_callback(request_id, response, exception):
            if exception is not None:
                print(f'URL提交失败 - ID: {request_id}, 异常: {exception}')
            else:
                url = response['urlNotificationMetadata']['url']
                successful.append(url)
                print(f'URL提交成功: {url}')
        
        batch = service.new_batch_http_request(callback=index_api_callback)
        for url, api_type in requests_dict.items():
            batch.add(service.urlNotifications().publish(
                body={"url": url, "type": api_type}))
        
        print("开始批量提交URL到谷歌索引API...")
        batch.execute()

        if successful:
            save_successful_urls(successful)
        else:
            print("本次无URL提交成功")
            
    except Exception as e:
        print(f"提交过程中发生错误: {e}")
        return []
    
    return successful


if __name__ == "__main__":
    successful_urls = publish()
    print(f"\n本次提交成功的URL总数: {len(successful_urls)}")
    if successful_urls:
        print("成功提交的URL列表:")
        for url in successful_urls:
            print(f"- {url}")