import json, os

LOCACLE_PATHS = {
    'ko-kr': os.path.join('locale', 'ko-kr.json')
    }


class Translator:
    def __init__(self, paths:dict=LOCACLE_PATHS):
        self.translator_table = dict()
        for lang, path in paths.items():
            with open(path, encoding='utf-8') as f:
                self.translator_table[lang] = json.load(f)

    def get_command_aliases(self, fname):
        aliases = list()
        for lang, table in self.translator_table.items():
            aliases.append(table['commands'][fname])
        return aliases

if __name__ == '__main__':
    t = Translator()
    print(t.get_command_aliases('store'))