import os.path

import requests


class DownloadFiles:

    def __init__(self):
        self.url = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2022/arqurnatot/"
        self.base_file_name = "bu_imgbu_logjez_rdv_vscmr_2022_{}t_{}.zip"
        self.turnos = [1, 2]
        self.ufs = [
            'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO', 'ZZ'
        ]
        self.response = None

    def execute(self):
        for uf in self.ufs:
            for turno in self.turnos:
                file_name = self.base_file_name.format(turno, uf)
                file_url = self.url + file_name
                if not os.path.isfile(file_name):
                    self._download(file_url)._save(file_name)
                print(f"[FINISHED] {file_name}")
        return self

    def _download(self, file_url):
        print(f"[Downloading...] {file_url}")
        self.response = requests.get(file_url)
        return self

    def _save(self, file_name):
        print(f"[Saving...] {file_name}")
        with open(file_name, 'wb') as f:
            f.write(self.response.content)
        return self


if __name__ == '__main__':
    DownloadFiles().execute()
