from dataclasses import dataclass
from pathlib import Path
import click
from funcs import parse_line, recognize_args, code_arg, get_ascii_text


@dataclass
class Command:
    name: str
    opcode: str
    has_ss: bool = False
    has_dd: bool = False
    has_nn: bool = False
    has_r: bool = False
    has_xx: bool = False

    print_shift: bool = False


COMMANDS = {
    "mov": Command(name="mov", opcode="0001", has_ss=True, has_dd=True),
    "movb": Command(name="movb", opcode="1001", has_ss=True, has_dd=True),
    "add": Command(name="add", opcode="0110", has_ss=True, has_dd=True),
    "halt": Command(name="halt", opcode="0" * 16),
    "sob": Command(name="sob", opcode="0111111", has_nn=True, has_r=True),
    "br": Command(name="br", opcode="00000001", has_xx=True),
    "clr": Command(name="clr", opcode="0000101000", has_dd=True),
    "beq": Command(name="beq", opcode="00000011", has_xx=True),
    "tstb": Command(name="tstb", opcode="1000101111", has_dd=True),
    "bpl": Command(name="bpl", opcode="10000000", has_xx=True),
    "jsr": Command(
        name="jsr", opcode="0000100", has_r=True, has_dd=True, print_shift=True
    ),
    "rts": Command(name="jsr", opcode="0000000010000", has_r=True),
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
        self.programm_counter = 0  # f'{:06o}'
        # Адрес текущего блока
        self.curr_block = 0  # f'{:04x}'
        self.object_lines[self.curr_block] = list()
        # Словарь для меток, собранных при прекомпиляции, здесь (имя метки): [номер строки с меткой, programm_counter]
        self.labels = dict()
        # Словарь для имен переменных, собранных при прекомпиляции, здесь (имя переменной): [значение]
        self.variables = dict()

    def precompile(self, filename: str | Path) -> None:
        """
        Выполняет парсинг программы из filename, сохраняет результат парсинга,
        параллельно собирает переменные программы
        :param filename: имя файла-исходника
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
                if str_dict.get("pseudo"):
                    commands = self.code_pseudo_command(
                        name=str_dict["pseudo"],
                        args=str_dict["arg"],
                        text=str_dict["text"],
                    )

                elif str_dict.get("name"):
                    commands, arguments = self.code_command(
                        name=str_dict["name"], args=str_dict["arg"], precompile=True
                    )
                    for arg_dict in arguments:
                        bin_line, plus_PC = self.recgnz_mode(arg_dict)
                        if plus_PC:
                            commands.append(bin_line)

                if str_dict.get("label"):
                    # Сохраняем адрес метки для дальнейшей компиляции
                    self.labels[str_dict["label"]] = {
                        "fileline_num": len(self.file_lines) - 1,
                        "programm_counter": self.programm_counter,
                    }

                if str_dict.get("variable"):
                    # Сохраняем значение переменной для дальнейшей компиляции
                    self.variables[str_dict["variable"]] = str_dict["arg"][0]

                for comm in commands:
                    # Увеличиваем programm_counter (+2 для word, +1 для byte)
                    self.programm_counter += len(comm) // 8

        # После прекомпиляции зануляем PC для дальнейшей компиляции
        self.programm_counter = 0

    def compile(self, filename: str | Path) -> None:
        """
        Компилирует файл filename, записывая filename.o и filename.l - байт-код и листинг файлы.
        :param filename: имя файла-исходника
            '01_sum.pdp'
        """
        self.precompile(filename)
        self.code_programm()

        self.write_obj(filename=filename + ".o")
        self.write_listing(filename=filename + ".l")

    @classmethod
    def bin(cls, number: int, width: int = 6) -> str:
        """
        Из строки (слова) в десятичном виде возвращет
        строчное числа в двоичной системе
        Также отдельно обрабатывает отрицательные числа
        :param number: число в десятичной системе
            -3
        :param width: длина результата
            8
        :return: 11111101
        """

        result = f"{abs(number):0{width}b}"

        if number < 0:
            number_unsigned = (1 << width) + number
            result = f"{number_unsigned:{width}b}"

        return result

    @classmethod
    def oct(cls, number: int, width: int = 6) -> str:
        """
        Принимает десятичное число и возвращает
        строчное восьмеричное представление числа
        дополненное нулями до длины width
        :param number: десятичное число
            10
        :param width: длина, до которой надо дополнить число
            6
        :return:
            000012
        """
        return f"{number:0{width}o}"

    @classmethod
    def bin2hex(cls, str_binword: str) -> list[str]:
        """
        Из строки (слова) в бинарном виде возвращет список hex байт (младший, старший)
        :str_binword: бинарном число
            0000111000111000
        :return:
            ['0e\n', '38\n']
        """
        if not str_binword:
            return []
        # Для word возвращаем два байта
        if len(str_binword) == 16:
            return [
                f"{int(str_binword[8:], 2):02x}\n",
                f"{int(str_binword[:8], 2):02x}\n",
            ]
        # Для byte возвращаем один байт
        elif len(str_binword) == 8:
            return [f"{int(str_binword[:8], 2):02x}\n"]

    @classmethod
    def bin2oct(cls, text: str) -> str:
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

        if text == "":
            return ""

        # Для word
        if len(text) == 16:
            res = text[0]
            for i in range(1, len(text), 3):
                res += f"{int(text[i : i + 3], 2):o}"
            return f"{int(res):06}"

        # Для byte
        elif len(text) == 8:
            res = f"{int(text[:2], 2):o}"
            for i in range(2, len(text), 3):
                res += f"{int(text[i : i + 3], 2):o}"
            return f"{int(res):03}"

    def resolve_args(self, parsed_args: list[dict], precompile: bool = False) -> None:
        """Подставляет вмесло переменной её значение
        :param parsed_args: список словарей, соответсвующих разобранным аргументам
        :param precompile: флаг режима прекомпиляции
        """

        # Подставляем реальные значения только при компиляции
        for arg in parsed_args:
            # Проверяем константы на десятичную точку
            if arg.get("const"):
                if arg["const"][-1] == ".":
                    arg["const"] = oct(int(arg["const"]))[2:]

            # Обрабатываем символы ASCII
            if arg.get("symbol"):
                arg["const"] = oct(ord(arg["symbol"]))[2:]
                arg.pop("symbol")

            # Если в аргументе нет переменной, то он уже готов
            if arg.get("variable") is None:
                continue

            # В прекомпиляции на этом resolve закончен
            if precompile:
                continue

            # Если есть такая метка - заменяем на её адрес
            elif self.labels.get(arg["variable"]):
                value = self.labels[arg["variable"]]["programm_counter"]
                arg["const"] = str(oct(value)[2:])
                if arg["mode"][0] != "6":
                    arg.pop("variable")

            # Если есть такая перeменная - заменяем на её значение
            elif self.variables.get(arg["variable"]):
                value = self.variables[arg["variable"]]
                arg["const"] = f"{int(value):06}"
                arg.pop("variable")

    def code_command(
        self,
        name: str,
        args: list[str] | None = None,
        precompile: bool = False,
        **kwargs,
    ) -> tuple[list[str], list[dict]]:
        """
        Берет команду name с аргументами args.
        Возвращает список слов в виде строк, в которые они кодируются.
        :param name: имя команды
            'mov'
        :param args:
            ['#2', 'R0']
        :param precompile: флаг режима прекомпиляции
            False
        :param kwargs: прочий мусор, который нам не нужен
        :return:
            ['012700', '000002']
        """
        # Получили информацию о нужной команде
        command = COMMANDS[name]

        # Первично разобрали аргументы
        args = args or []
        parsed_args: list[dict] = recognize_args(args) if args else {}
        # Вторично разобрали перемненные в аргументах
        self.resolve_args(parsed_args, precompile)
        code_n = command.opcode

        # Инициировали кодировки аргументов
        code_r = code_nn = code_ss = code_dd = code_xx = ""

        # Кодируем каждый тип
        if command.has_r:
            # R всегда первый
            reg = parsed_args[0]
            code_r = code_arg(reg)[3:]

        if command.has_nn:
            # В режиме прекомпиляции вставляем заполнитель
            if precompile:
                code_nn = "0" * 6
            else:
                # NN всегда последний
                N_shift = (
                    self.programm_counter
                    + 2
                    - self.labels[args[-1]]["programm_counter"]
                )
                code_nn = self.bin(N_shift // 2)

        if command.has_dd:
            # DD всегда последний
            arg_dd = parsed_args[-1]
            code_dd = code_arg(arg_dd)

        if command.has_ss:
            # SS первый если нет R, второй если есть
            arg_ss = parsed_args[command.has_r]
            code_ss = code_arg(arg_ss)

        if command.has_xx:
            # В режиме прекомпиляции вставляем заполнитель
            if precompile:
                code_xx = "0" * 8
            else:
                # XX всегда одинок
                N_shift = self.labels[args[-1]]["programm_counter"] - (
                    self.programm_counter + 2
                )
                code_xx = self.bin(N_shift // 2, width=8)

        # Некоторым командам необходимо дополнительно записать Сдвиг по метке,
        # Но этот сдвиг обусловнен не модой, а спецификой команды
        # В случаях других команд, аргумент метки выгдядит точно так же (та же мода, то же написание)
        # Но при этом ничего не печатаем
        # Поэтому печать сдвига обрабатываем отдельно
        if command.print_shift:
            mode = "2"

            # В режиме прекомпиляции вставляем заполнитель
            if precompile:
                parsed_args.append({"const": "0", "mode": mode})
            else:
                shift = self.labels[args[-1]]["programm_counter"] - (
                    self.programm_counter + 4
                )

                parsed_args.append({"const": self.oct(shift), "mode": mode})

        # Возможные варианты DD, SSDD, RSS, RDD, R, RNN, XX, NN или ничего
        code_com = code_n + code_r + code_ss + code_dd + code_nn + code_xx

        return [
            code_com,
        ], parsed_args

    def code_pseudo_command(self, name: str, args: dict, text: str) -> list[str]:
        """
        Разбираем псевдокоманду и выполняем её.
        Возвращаем необходимые дополнительные байты и слова.
        :param name: имя псевдо псевдокоманды
            '.='
        :param args: аргументы псевдокоманды
            ['1000']
        :param text: текст строки с командой
            '.= 1000'
        :return:
            []
        """

        match name:
            case ".=":
                address = int(args[0], 8)
                self.programm_counter = address
                self.curr_block = address
                self.object_lines[address] = list()
                return []

            case ".WORD" | ".BYTE":
                number_lines = []
                for arg in args:
                    arg_ = arg
                    if arg[-1] == ".":
                        arg_ = oct(int(arg))[2:]
                    elif arg[0] == "'":
                        arg_ = oct(ord(arg))[2:]
                    number = int(arg_, 8)
                    width_ = 16 if name==".WORD" else 8
                    bin_line = self.bin(number, width=width_)
                    number_lines.append(bin_line)
                return number_lines

            case ".ASCII" | ".ASCIZ":
                number_lines = []
                # Выделяем из text аргумент
                string_arg = get_ascii_text(name=name, text=text)
                # Кодируем посимвольно
                for symbol in string_arg:
                    bin_line = self.bin(ord(symbol), width=8)
                    number_lines.append(bin_line)
                # Специфика .ASCIZ - в конце добавляем нуль
                if name == ".ASCIZ" :
                    number_lines.append("0" * 8)
                return number_lines

    def recgnz_mode(self, arg: dict, current_counter: int = 0) -> tuple[str, bool]:
        """
        Принимает словарь с ключами 'mode' и 'reg'|'const'|'symbol'|'variable'
        Возвращает если необходимо восьмеричные данные,
        необходимые для реализации специфичной моды
        Для моды 2 регистра R7 вернет восьмеричное представление константы
        :param  arg: словарь характеристик аргумента
            {'mode': ['2'], 'const': '2'}
        :param current_counter: PC на котором будет распологаться слово
            001012
        :return:
            '000002'
        """
        # Заполитель для режима прекомпиляции
        if arg.get("variable") and arg["mode"][0] != "6":
            return "0" * 16, True

        if arg.get("reg") or arg.get("variable"):
            # Обрабатываем сдвиг
            if arg.get("shift"):
                shift = int(arg["shift"], 8)
                width = 16
                result = abs(shift)
                if shift < 0:
                    result = (1 << width) + shift
                return f"{result:0{width}b}", True
            return "", False

        mode = arg["mode"][0]

        if arg.get("const"):
            number = int(arg["const"], 8)
            width = 16
            result = abs(number)
            if number < 0:
                result = (1 << width) + number

            # Обрабатываем сдвиг для шестой моды
            if mode == "6":
                result = result - (current_counter)
                if result < 0:
                    result = (1 << width) + result
            return f"{result:0{width}b}", True

        return "", False

    def code_programm(self) -> None:
        """
        Формурует строки для .o и .l файлов
        """
        for str_dict in self.parsed_lines:
            # Нужно зафиксировать programm_counter до его возможного изменения в code_pseudo_command
            current_counter = self.programm_counter
            if str_dict.get("pseudo"):
                commands = self.code_pseudo_command(
                    name=str_dict["pseudo"], args=str_dict["arg"], text=str_dict["text"]
                )
            elif str_dict.get("name"):
                commands, arguments = self.code_command(
                    name=str_dict["name"], args=str_dict["arg"]
                )

                # Сохраняем programm_counter команды для разбора аргументов и их мод
                argument_counter = current_counter + 2
                for arg_dict in arguments:
                    bin_line, plus_PC = self.recgnz_mode(arg_dict, argument_counter + 2)
                    if plus_PC:
                        argument_counter += 2
                        commands.append(bin_line)
            else:
                commands = []

            self.listing_comm(str_dict, commands, current_counter)
            self.object_comm(commands)

    def listing_comm(
        self, str_dict: dict, commands: list[str], current_counter: int
    ) -> None:
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
        if str_dict["text"] != "":
            # В каком адресе лежит какая команда
            self.lines.append(self.oct(current_counter) + ":\t\t" + str_dict["text"])

        # Печатаем байты "лесенкой"
        tabulation_for_byte = 0
        for cmd in commands:
            tabulation_for_byte = 0 if tabulation_for_byte else 1
            if len(cmd) == 8 and tabulation_for_byte:
                self.lines.append(f"\t\t{self.bin2oct(cmd)}")
            else:
                self.lines.append(f"\t{self.bin2oct(cmd)}")
            self.programm_counter += len(cmd) // 8

    def object_comm(self, commands: list[str]) -> None:
        """
        Из списка слов или байт делает код для объектного файла
        :param commands:
            ['']
            ['012700', '000002']
        Добавляет для этих словарей в self.object_lines строки
            с0
            15
            02
            00
        """
        # Cчитаем, что тут всегда есть блок (как минимум - нулевой)
        obj_bytes: list[str] = self.object_lines[self.curr_block]
        for word in commands:
            for byte in self.bin2hex(word):
                obj_bytes.append(byte)

    def write_listing(self, filename: str | Path) -> None:
        """
        Формируем .l из собранной информации.
        :param filename: имя файла-исходника
            '01_sum.pdp'
        """
        with open(Path.cwd() / filename, mode="w") as file:
            file.write("\n".join(self.lines))

    def write_obj(self, filename: str | Path) -> None:
        """
        Формируем .o из собранной информации.
        :param filename: имя файла-исходника
            '01_sum.pdp'
        """
        with open(Path.cwd() / filename, mode="w") as file:
            for block_address, block_bytes in self.object_lines.items():
                if len(block_bytes) != 0:
                    file.write(f"{block_address:x}" + " " + f"{len(block_bytes):04x}\n")
                    file.write("".join(block_bytes))


@click.command()
@click.argument("filename")
def compile_programm(filename: str | Path):
    p = PDP11_Parser()
    p.compile(filename)


if __name__ == "__main__":
    compile_programm()
