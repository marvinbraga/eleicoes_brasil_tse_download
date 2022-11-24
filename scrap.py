import os

import requests
from bs4 import BeautifulSoup


class ScrapTseData:

    def __init__(self):
        page = requests.get(
            'https://dadosabertos.tse.jus.br/dataset/resultados-2022-arquivos-transmitidos-para-totalizacao'
        )
        self._soup = BeautifulSoup(page.content, features="html.parser")
        self._zip_file = 'zip_files.txt'

    def __del__(self):
        if os.path.isfile(self.zip_file):
            os.remove(self.zip_file)

    @property
    def zip_file(self):
        return self._zip_file

    def _get_files(self):
        if os.path.isfile(self.zip_file):
            os.remove(self.zip_file)
        with open(self.zip_file, 'w') as newfile:
            for anchor in self._soup.findAll('a', {'class': 'resource-url-analytics'}, href=True):
                links = anchor['href']
                if links.endswith('.zip'):
                    newfile.write(links + '\n')
        return self

    def execute(self):
        self._get_files()
        return self


class DownloadTseData:

    def __init__(self, scrapper):
        self.scrapper = scrapper
        self.response = None

    @staticmethod
    def _get_filename(url):
        res = url.split('/')[-1]
        return res[:-1]

    def _get_files(self):
        self.scrapper.execute()
        return self

    def _get_links(self):
        with open(self.scrapper.zip_file, 'r') as links:
            result = links.readlines()
        return result

    def _download_files(self):
        count = 0
        links = self._get_links()
        for link in links:
            count += 1
            filename = self._get_filename(link)
            if not os.path.isfile(filename):
                self._download(link[:-1])._save(filename)
            print(f'[FINISHED ({count}/{len(links)})] {filename}')
        return self

    def _download(self, file_url):
        print(f'[Downloading...] {file_url}')
        self.response = requests.get(file_url)
        return self

    def _save(self, file_name):
        print(f'[Saving...] {file_name}')
        with open(file_name, 'wb') as output_file:
            output_file.write(self.response.content)
        return self

    def execute(self):
        self._get_files()._download_files()
        return self


if __name__ == '__main__':
    DownloadTseData(scrapper=ScrapTseData()).execute()
