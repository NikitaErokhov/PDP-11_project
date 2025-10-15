from pathlib import Path
import click
from my_funcs import parse_line, recgnz_comm, \
    recgnz_args, bin_to_oct, code_arg, recgnz_mode


class PDP11_Parser:
    def __init__(self):
        # Список строк, прочитанных из файла
        self.file_lines = []
        # Список словарей полученных при парсинге строк, прочитанных из файла
        self.parsed_lines = []
        # Список для формирования .l файла, здесь [строки .l файла по порядку]
        self.lines = []
        # PC
        self.programm_counter = 0   # f'{:06o}'
        # Словарь для формирования .о файла, здесь (адрес блока): [байты блока по порядку]
        self.object_lines = dict()
        # Адрес текущего блока
        self.curr_block = 0         # f'{:04x}'
        self.object_lines[self.curr_block] = list()
        # Словарь для меток, собранных при прекомпиляции, здесь (имя метки): [номер строки с меткой, programm_counter]
        self.labels = dict()

    def precompile(self, filename: str | Path):
        """
        Выполняет парсинг программы из filename, сохраняет результат парсинга,
        параллньно собирает метки программы
        :param filename: имя файла программы
            '01_sum.pdp'
        """
        with open(filename) as file:
            for file_string_ in file:
                file_string_ = file_string_.rstrip()
                if not file_string_:
                    continue

                # Строку полностью не теряем
                self.file_lines.append(file_string_)
                str_dict = parse_line(file_string_)

                # Сохранили результат для использования в code_programm
                self.parsed_lines.append(str_dict)

                # Обрабатываем команды, чтобы получить верный programm_counter
                commands = []
                if str_dict.get('pseudo'):
                    commands = self.code_pseudo_command(name=str_dict['pseudo'],
                                                        args=str_dict['arg'])
                    arguments = []
                elif str_dict.get('name'):
                    commands, arguments = self.code_command(name=str_dict['name'],
                                                            args=str_dict['arg'])
                    for arg_dict in arguments:
                        bin_line, plus_PC = recgnz_mode(arg_dict)
                        if plus_PC:
                            commands.append(bin_line)

                if str_dict.get('lable'):
                    self.labels[str_dict['lable']] = {
                        "fileline_num": len(self.file_lines)-1, 
                        "programm_counter": self.programm_counter}

                self.programm_counter += 2 * len(commands)
        self.programm_counter = 0

    def compile(self, filename: str | Path):
        """Компилирует файл filename, записывая filename.o и filename.l - байт-код и листинг файлы."""

        self.precompile(filename)

        self.code_programm()

        self.write_obj(filename=filename+'.o')
        self.write_listing(filename=filename+'.l')

    @classmethod
    def oct(cls, number: int,  width: int = 6):
        # TODO: потом что-то сделать с ширирой, чтобы байты печатать
        return f"{number:06o}"

    @classmethod
    def bin2hex(cls, str_binword: str) -> list[str]:
        """Из строки (слова) в бинарном виде возвращет список  hex байт (младший, старший)"""
        if not str_binword:
            return []
        return [f"{int(str_binword[8:], 2):02x}\n",
                f'{int(str_binword[:8], 2):02x}\n']

    def code_command(self, name: str, args: list[str] = list(), **kwargs):
        """
        Берет команду name с аргументами args.
        Возвращает список слов в виде строк, в которые они кодируются.
        :param name: имя команды
            'mov'
        :param args:
            ['#2', 'R0']
        :param kwargs: прочий мусор, который нам не нужен
        :return:
            ['012700', '000002']
        """
        # Получили кодировку команды в 2-ой системе счисления
        code_n = recgnz_comm(name)

        # Если попали на SOB
        if code_n == '0111111':
            N_shift = self.programm_counter+2 - \
                self.labels[args[1]]["programm_counter"]
            reg = recgnz_args([args[0]])
            code_R = code_arg(*reg)[3:]
            code_n += code_R
            code_NN = f'{N_shift//2:06b}'
            code_n += code_NN
            return [code_n], {}

        # Получили dict-ы с ключом mode и ключом reg|const|simb соотв. аргументов
        parse_a = recgnz_args(args) if args else {}
        # Конкатенируем аргументы к коду команды по порядку
        for arg_dict in parse_a:
            code_n += code_arg(arg_dict)

        return [code_n,], parse_a

    def code_pseudo_command(self, name: str, args: dict):
        """Разбираем псевдокоманду и выполняем ее."""
        match name:
            case '.=':
                address = int(args[0], 8)
                self.programm_counter = address
                self.curr_block = address
                self.object_lines[address] = list()
                return []

    def code_programm(self):
        """
        Формурует строки для .o и .l файлов
        :param filename: имя файла программы 
            '01_sum.pdp'
        """
        for str_dict in self.parsed_lines:

            if str_dict.get('pseudo'):
                # тут мы должны будем поменять адрес начала блока, если .=
                commands = self.code_pseudo_command(name=str_dict['pseudo'],
                                                    args=str_dict['arg'])
                arguments = []
            elif str_dict.get('name'):
                commands, arguments = self.code_command(name=str_dict['name'],
                                                        args=str_dict['arg'])
                for arg_dict in arguments:
                    bin_line, plus_PC = recgnz_mode(arg_dict)
                    if plus_PC:
                        commands.append(bin_line)
            else:
                commands = []

            self.listing_comm(str_dict, commands)
            self.object_comm(commands)

    def listing_comm(self, str_dict: dict, commands: list[str]):
        """
        Из словаря, который описывает строку делает 1+ строк листинга
        :param str_dict:
            {'name': '=', 'arg': '1000', 'text': '	. = 1000;', 'pseudo': True}
            {'name': 'mov', 'args': ['R0', 'R1'], 'text': '	mov 	#2, R0; R0 = 2'}
        :param commands:
            ['']
            ['012700', '000002']
        Добавляет для этих словарей в self.listing строки
        000000:		. =		1000
        001000:		mov		#2, R0
            012700
            000002
        """
        if str_dict['text'] != '':
            # В каком адресе лежит какая команда
            self.lines.append(self.oct(self.programm_counter) + ':\t\t' +
                              str_dict['text'])

        for cmd in commands:
            self.lines.append(f"\t{bin_to_oct(cmd)}")
        self.programm_counter += 2 * len(commands)

    def object_comm(self, commands: list[str]):
        """
        Из списка слов делает код для объектного файла (TODO: или байт)
        :param commands:
            ['']
            ['012700', '000002']
        Добавляет для этих словарей в self.listing строки
        000000:		. =		1000
        001000:		mov		#2, R0
            012700
            000002
        """
        # считаем, что тут всегда есть блок
        obj_bytes: list[str] = self.object_lines[self.curr_block]
        for word in commands:
            for byte in self.bin2hex(word):
                obj_bytes.append(byte)

    def write_listing(self, filename: str | Path):
        """Формируем .l из собранной информации."""
        with open(Path.cwd() / filename, mode='w') as file:
            file.write('\n'.join(self.lines))

    def write_obj(self, filename: str | Path):
        """Формируем .o из собранной информации."""
        with open(Path.cwd() / filename, mode='w') as file:
            for block_address, block_bytes in self.object_lines.items():
                if len(block_bytes) != 0:
                    file.write(f"{block_address:x}" + ' ' +
                               f'{len(block_bytes):04x}\n')
                    file.write(''.join(block_bytes))


@click.command()
@click.argument('filename')
def compile_programm(filename: str | Path):
    p = PDP11_Parser()
    p.compile(filename)


if __name__ == "__main__":
    compile_programm()
