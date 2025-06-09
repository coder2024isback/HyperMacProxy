from flask import request
import requests
from bs4 import BeautifulSoup, Comment
import urllib.parse

DOMAIN = "wikipedia.org"

def create_search_form():
    return '''
    <br>
    <center>
        <h6><font size="7" face="Times"><b>WIKIPEDIA</b></font><br>The Free Encyclopedia</h6>
        <form action="/wiki/" method="get">
            <input size="35" type="text" name="search" required>
            <input type="submit" value="Search">
        </form>
    </center>
    '''

def get_featured_article_snippet():
    try:
        response = requests.get("https://en.wikipedia.org/wiki/Main_Page")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        tfa_div = soup.find('div', id='mp-tfa')
        if tfa_div:
            first_p = tfa_div.find('p')
            if first_p:
                return f'<br><br><b>From today\'s featured article:</b>{str(first_p)}'
    except Exception as e:
        print(f"Error fetching featured article: {str(e)}")
    return ''

def process_html(content, title):
    return f'<html><head><title>{title.replace("_", " ")}</title></head><body><font face="Times">{content}</font></body></html>'

def handle_request(req):
    if req.method == 'GET':
        path = req.path.lstrip('/')
        if not path or path == 'wiki/':
            search_query = req.args.get('search', '')
            if not search_query:
                content = create_search_form() + get_featured_article_snippet()
                return process_html(content, "Wikipedia"), 200
            return handle_wiki_page(search_query)

        if path.startswith('wiki/'):
            page_title = urllib.parse.unquote(path.replace('wiki/', ''))
            return handle_wiki_page(page_title)

    return "Method not allowed", 405

def handle_wiki_page(title):
    search_url = f"https://{DOMAIN}/w/api.php"
    params = {
        "action": "query", "format": "json", "list": "search",
        "srsearch": title, "srprop": "", "utf8": 1
    }

    try:
        search_response = requests.get(search_url, params=params)
        search_response.raise_for_status()
        search_data = search_response.json()

        if not search_data["query"]["search"]:
            return process_html("<p>No results found.</p>", f"Search - Wikipedia"), 404

        found_title = search_data["query"]["search"][0]["title"]
        url = f"https://{DOMAIN}/wiki/{urllib.parse.quote(found_title)}"
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        title_element = soup.select_one('span.mw-page-title-main')
        page_title = title_element.text if title_element else found_title.replace('_', ' ')

        header_table = f'''
        <table width="100%">
            <tr>
                <td valign="bottom"><h5><font size="5" face="Palatino"><b>{page_title}</b></font></h5></td>
                <td align="right" valign="middle">
                    <form action="/wiki/" method="get">
                        <input size="20" type="text" name="search" required>
                        <input type="submit" value="Go">
                    </form>
                </td>
            </tr>
        </table><hr>
        '''

        content_div = soup.select_one('div#mw-content-text')
        if not content_div:
            return process_html(header_table + "<p>Content not found.</p>", page_title), 200

        # Strips
        for selector in [
            'table.infobox', 'figure', 'div.shortdescription', 'table.ambox',
            'style', 'script', 'span.mw-editsection', 'link', 'noscript',
            'div.printfooter', 'div.refbegin', 'div.quotebox', 'div.navbox',
            'div.navbox-styles', 'div.thumb', 'div.reflist', 'div.sistersitebox',
            'div#catlinks', 'table.sidebar', 'table.wikitable', 'table.mw-collapsible',
            'ul.gallery', 'img', 'sup'
        ]:
            for tag in content_div.select(selector):
                tag.decompose()

        # Convert <h2>.. to styled <b><font>
        for h in content_div.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
            size = {"h2": "4", "h3": "3", "h4": "3", "h5": "2", "h6": "2"}.get(h.name, "3")
            face = {"h5": "Palatino", "h6": "Times"}.get(h.name, "Times")
            text = h.get_text()
            replacement = BeautifulSoup(
                f'<br><br><b><font size="{size}" face="{face}">{text}</font></b><hr>', 'html.parser'
            )
            h.replace_with(replacement)

        # Unwrap <i>, convert <a>, and replace <ul> bullets
        for tag in content_div.find_all('i'):
            tag.unwrap()
        for a in content_div.find_all('a'):
            a['style'] = "text-decoration: underline; color: blue"
        for ul in content_div.find_all('ul'):
            for li in ul.find_all('li'):
                li.insert_before('• ')
            ul.unwrap()

        for comment in content_div.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        content = header_table + str(content_div)
        return process_html(content, f"{page_title} - Wikipedia"), 200

    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response.status_code == 404:
            return process_html("<p>Page not found.</p>", "Wikipedia Error"), 404
        return process_html(f"<p>Error: {str(e)}</p>", "Wikipedia Error"), 500

    except Exception as e:
        return process_html(f"<p>Error: {str(e)}</p>", "Wikipedia Error"), 500
