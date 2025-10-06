from pathlib import Path
import sys
from my_funcs import parse_comm, recgnz_comm, \
    recgnz_args, bin_to_oct, code_arg, recgnz_mode


class PDP11_Parser:
    def __init__(self):
        # Список для формирования .l файла, здесь [строки .l файла по порядку]
        self.lines = []
        # PC
        self.programm_counter = 0   # f'{:06o}'
        # Словарь для формирования .о файла, здесь (адрес блока): [байты блока по порядку]
        self.object_lines = dict()
        # # Словарь для формирования .trace файла, здесь (имя раздела): [строки раздела по порядку]
        # self.trace_lines: dict[list] = dict()
        # self.trace_lines['running'] = list()
        # self.trace_lines['halted'] = list()

        # self.registers = {'r0': 0,
        #                   'r1': 0,
        #                   'r2': 0,
        #                   'r3': 0,
        #                   'r4': 0,
        #                   'r5': 0,
        #                   'sp': 0,
        #                   'pc': 0,
        #                   }
        # Адрес текущего блока
        self.curr_block = 0         # f'{:04x}'

    def compile(self, filename: str | Path):
        """Компилирует файл filename, записывая filename.o и filename.l - байт-код и листинг файлы."""
        self.parse_programm(filename=filename)
        self.write_obj(filename=filename+'.o')
        self.write_listing(filename=filename+'.l')
        # self.write_trace(filename=filename+'.trace')

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

    def code_command(self, name: str, args: list[str], **kwargs):
        """
        Берет команду name с аргументами args.
        Возвращает список слов в виде строк, в которые они кодируются.
        :param name: имя команды 'mov'
        :param args: ['#2', 'R0']
        :param kwargs: прочий мусор, который нам не нужен
        :return: ['012700', '000002']
        """
        # Получили кодировку команды в 2-ой системе счисления
        code_n = recgnz_comm(name)
        # Получили dict-ы с ключом mode и ключом reg|const|simb соотв. аргументов
        parse_a = recgnz_args(args) if args else {}
        # Конкатенируем аргументы к коду команды по порядку
        for arg_dict in parse_a:
            code_n += code_arg(arg_dict)

        return [code_n,], parse_a

    def parse_programm(self, filename: str | Path):
        with open(filename) as file:
            for key in file:
                key = key.rstrip()
                if not key:
                    # пустая строка
                    # self.lines.append(self.programm_counter + ':\t')
                    self.listing_comm({}, [])
                    continue

                # В непустой лежит команда или проч. - парсим
                str_dict = parse_comm(key)
                if str_dict.get('pseudo'):
                    # тут мы должны будем поменять адрес начала блока, если .=
                    commands = self.code_pseudo_command(name=str_dict['pseudo'],
                                                        args=str_dict['arg'])
                    arguments = []
                else:
                    commands, arguments = self.code_command(name=str_dict['name'],
                                                            args=str_dict['arg'])
                    for arg_dict in arguments:
                        bin_line, raise_PC = recgnz_mode(arg_dict)
                        if raise_PC:
                            commands.append(bin_line)
                    # self.trace_comm(str_dict=str_dict, args=arguments)

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
        # В каком адресе лежит какая команда
        self.lines.append(self.oct(self.programm_counter) + ':\t\t' +
                          str_dict['text'])

        for cmd in commands:
            self.lines.append(f"\t{bin_to_oct(cmd)}")
        self.programm_counter += 2 * len(commands)
        # self.registers['pc'] = self.programm_counter

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

    # def trace_comm(self, str_dict: dict, args: list[dict]):
    #     line_ = self.oct(self.programm_counter) + ':\t\t'
    #     line_ += str_dict['name'] + '\t\t'
    #     line_ += ', '.join(str_dict['arg'])
    #     self.execute_comm(str_dict=str_dict, args=args)
    #     self.trace_lines['running'].append(line_)

    def code_pseudo_command(self, name: str, args: dict):
        """Разбираем псевдокоманду и выполняем ее."""
        match name:
            case '. =':
                address = int(args[0], 8)
                self.programm_counter = address
                # self.registers['pc'] = self.programm_counter
                self.curr_block = address
                self.object_lines[address] = list()
                return []

    def write_listing(self, filename: str | Path):
        """Формируем .l из собранной информации."""
        with open(Path.cwd() / filename, mode='w') as file:
            file.write('\n'.join(self.lines))

    def write_obj(self, filename: str | Path):
        """Формируем .o из собранной информации."""
        with open(Path.cwd() / filename, mode='w') as file:
            for block_address, block_bytes in self.object_lines.items():
                file.write(f"{block_address:x}" + ' ' +
                           f'{len(block_bytes):04x}\n')
                file.write(''.join(block_bytes))

    # def write_trace(self, filename: str | Path):
    #     """Формируем .trace из собранной информации."""
    #     with open(Path.cwd() / filename, mode='w') as file:
    #         for name, strings in self.trace_lines.items():
    #             file.write('-'*7 + name + '-'*7 + '\n')
    #             file.write('\n'.join(strings))
    #             file.write('\n')


if __name__ == "__main__":
    p = PDP11_Parser()
    p.compile(sys.argv[1])
