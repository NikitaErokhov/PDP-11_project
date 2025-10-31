from dataclasses import dataclass
from pathlib import Path
import click
from my_funcs import parse_line, \
    recgnz_args, code_arg, recgnz_mode


@dataclass
class Command:
    name: str
    opcode: str
    has_ss: bool = False
    has_dd: bool = False
    has_nn: bool = False
    has_r: bool = False
    has_xx: bool = False


COMMANDS = {
    'mov': Command(name='mov', opcode='0001', has_ss=True, has_dd=True),
    'movb': Command(name='movb', opcode='1001', has_ss=True, has_dd=True),
    'add': Command(name='add', opcode='0110', has_ss=True, has_dd=True),
    'halt': Command(name='halt', opcode='0'*16),
    'sob': Command(name='sob', opcode='0111111', has_nn=True, has_r=True),
    'br': Command(name='br', opcode='00000001', has_xx=True),
    'clr': Command(name='clr', opcode='0000101000', has_dd=True),
    'beq': Command(name='beq', opcode='00000011', has_xx=True),

}


class PDP11_Parser:
    def __init__(self):
        # Список строк, прочитанных из файла
        self.file_lines = []
        # Список словарей полученных при парсинге строк, прочитанных из файла
        self.parsed_lines: list[dict] = []
        # Список для формирования .l файла, здесь [строки .l файла по порядку]
        self.lines: list[str] = []
        # Словарь для формирования .о файла, здесь (адрес блока): [байты блока по порядку]
        self.object_lines = dict()
        # PC
        self.programm_counter = 0   # f'{:06o}'
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

                elif str_dict.get('name'):
                    commands, arguments = self.code_command(name=str_dict['name'],
                                                            args=str_dict['arg'],
                                                            precompile=True)
                    for arg_dict in arguments:
                        bin_line, plus_PC = recgnz_mode(arg_dict)
                        if plus_PC:
                            commands.append(bin_line)

                if str_dict.get('label'):
                    self.labels[str_dict['label']] = {
                        "fileline_num": len(self.file_lines)-1,
                        "programm_counter": self.programm_counter}

                for comm in commands:
                    self.programm_counter += len(comm)//8
        # После прекомпиляции зануляем PC для code_programm
        self.programm_counter = 0

    def compile(self, filename: str | Path):
        """Компилирует файл filename, записывая filename.o и filename.l - байт-код и листинг файлы."""

        self.precompile(filename)

        self.code_programm()

        self.write_obj(filename=filename+'.o')
        self.write_listing(filename=filename+'.l')

    @classmethod
    def bin(cls, number: int, width: int = 6):
        """Из строки (слова) в десятичном виде возвращет
        строчное числа в двоичной системе
        Также отдельно обрабатывает отрицательные числа
        :param number: число в десятичной системе
            -3
        :param width: длина результата
            8
        :return: 11111101"""

        result = f'{abs(number):0{width}b}'

        if number < 0:
            number_unsigned = (1 << width) + number
            result = f'{number_unsigned:{width}b}'

        return result

    @classmethod
    def oct(cls, number: int,  width: int = 6):
        # TODO: потом что-то сделать с ширирой, чтобы байты печатать
        return f"{number:0{width}o}"

    @classmethod
    def bin2hex(cls, str_binword: str) -> list[str]:
        """Из строки (слова) в бинарном виде возвращет список  hex байт (младший, старший)"""
        if not str_binword:
            return []
        if len(str_binword) == 16:
            return [f"{int(str_binword[8:], 2):02x}\n",
                    f'{int(str_binword[:8], 2):02x}\n']
        elif len(str_binword) == 8:
            return [f"{int(str_binword[:8], 2):02x}\n"]

    @classmethod
    def bin2oct(cls, text: str):
        """
        Принимает строку с двоичным 16-бит числом
        Возвращает число, где первый символ совпадает с первоым символом text,
        а все последующие являются восьмеричным представлением соответствующий трёх двоичных битов.
        :param  text: строка длиной width
            '0001010111000000'
        :param width: длина строки
            16
        :return:
            '012700'
        """
        if text == '':
            return ''
        if len(text) == 16:
            res = text[0]
            for i in range(1, len(text), 3):
                res += f"{int(text[i:i+3], 2):o}"
            return f"{int(res):06}"
        elif len(text) == 8:
            res = f"{int(text[:2], 2):o}"
            for i in range(2, len(text), 3):
                res += f"{int(text[i:i+3], 2):o}"
            return f"{int(res):03}"

    def resolve_args(self, parsed_args: list[dict], precompile: bool = False) -> None:
        """ Подставляет вмесло переменной её значение
        :param parsed_args: список словарей, соответсвующих разобранным аргументам
        """
        # Подставляем реальные значения только при компиляции
        for arg in parsed_args:
            # Если в аргументе нет переменной, то он уже готов
            if arg.get('variable') is None:
                return

            if precompile:
                value = 0
                arg['const'] = str(oct(value)[2:])
                arg.pop('variable')

            # Если есть такая метка
            elif self.labels.get(arg['variable']):
                value = self.labels[arg['variable']]["programm_counter"]
                arg['const'] = str(oct(value)[2:])
                arg.pop('variable')

    def code_command(self, name: str, args: list[str] | None = None, precompile: bool = False, ** kwargs):
        """
        Берет команду name с аргументами args.
        Возвращает список слов в виде строк, в которые они кодируются.
        :param name: имя команды
            'mov'
        :param args:
            ['#2', 'R0']
        :param precompile: флаг прекомпиляции
            False
        :param kwargs: прочий мусор, который нам не нужен
        :return:
            ['012700', '000002']
        """
        # Получили информацию о нужной команде
        command = COMMANDS[name]
        args = args or []
        parsed_args: list[dict] = recgnz_args(args) if args else {}

        # Разбираем переменные
        self.resolve_args(parsed_args, precompile)

        code_n = command.opcode

        # Инициировали кодировки аргументов
        code_r = code_nn = code_ss = code_dd = code_xx = ''

        # Кодируем каждый тип
        if command.has_r:
            # R всегда первый
            reg = parsed_args[0]
            code_r = code_arg(reg)[3:]

        if command.has_nn:
            if precompile:
                code_nn = '0'*6
            else:
                # NN всегда последний
                N_shift = self.programm_counter+2 - \
                    self.labels[args[-1]]["programm_counter"]
                code_nn = self.bin(N_shift//2)

        if command.has_dd:
            # DD всегда последний
            arg_dd = parsed_args[-1]
            code_dd = code_arg(arg_dd)

        if command.has_ss:
            # SS первый если нет R, второй если есть
            arg_ss = parsed_args[command.has_r]
            code_ss = code_arg(arg_ss)

        if command.has_xx:
            if precompile:
                code_xx = '0'*8
            else:
                # XX всегда одинок
                N_shift = self.labels[args[-1]]["programm_counter"]\
                    - self.programm_counter - 2
                code_xx = self.bin(N_shift//2, width=8)
        # Возможные варианты DD, SSDD, RSS, RDD, R, RNN, XX, NN или ничего
        code_com = code_n + code_r + code_ss + code_dd + code_nn + code_xx

        return [code_com,], parsed_args

    def code_pseudo_command(self, name: str, args: dict,):
        """Разбираем псевдокоманду и выполняем ее."""
        match name:
            case '.=':
                address = int(args[0], 8)
                self.programm_counter = address
                self.curr_block = address
                self.object_lines[address] = list()
                return []
            case '.WORD':
                number_lines = []
                for arg in args:
                    number = int(arg, 8)
                    bin_line = self.bin(number, width=16)
                    number_lines.append(bin_line)

                return number_lines
            case '.BYTE':
                number_lines = []
                for arg in args:
                    number = int(arg, 8)
                    bin_line = self.bin(number, width=8)
                    number_lines.append(bin_line)
                return number_lines

    def code_programm(self):
        """
        Формурует строки для .o и .l файлов
        :param filename: имя файла программы
            '01_sum.pdp'
        """
        for str_dict in self.parsed_lines:
            # Нужно зафиксировать programm_counter до его возможного изменения в code_pseudo_command
            current_counter = self.programm_counter
            if str_dict.get('pseudo'):
                commands = self.code_pseudo_command(name=str_dict['pseudo'],
                                                    args=str_dict['arg'])
            elif str_dict.get('name'):
                commands, arguments = self.code_command(name=str_dict['name'],
                                                        args=str_dict['arg'])
                for arg_dict in arguments:
                    bin_line, plus_PC = recgnz_mode(arg_dict)
                    if plus_PC:
                        commands.append(bin_line)
            else:
                commands = []

            self.listing_comm(str_dict, commands, current_counter)
            self.object_comm(commands)

    def listing_comm(self, str_dict: dict, commands: list[str], current_counter: int):
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
            self.lines.append(self.oct(current_counter) + ':\t\t' +
                              str_dict['text'])
        # Чтобы байты печатались в нужном формате
        tabulation_for_byte = 0
        for cmd in commands:
            tabulation_for_byte = 0 if tabulation_for_byte else 1
            if len(cmd) == 8 and tabulation_for_byte:
                self.lines.append(f"\t\t{self.bin2oct(cmd)}")
            else:
                self.lines.append(f"\t{self.bin2oct(cmd)}")
            self.programm_counter += len(cmd)//8

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
    # print(PDP11_Parser.bin2oct('11111011'))
    compile_programm()
