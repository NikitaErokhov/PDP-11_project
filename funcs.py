import pyparsing as pp
from re import VERBOSE


def parse_line(text: str) -> dict:
    """
    Принимает строку с командой
    Возвращает саму строку, а также выделенное имя команды, аргументы и комментарий
    :param  text: строка с командой
        "LOOP: mov 	#2, R0;"
        ".= 1000; some comment"
    :return:
        {"label": "LOOP", "name": "mov", "arg": ["#2", "R0"], "text": "LOOP: mov\t#2, R0;"}
        {"pseudo": ".=", "arg": ["1000"], "comm": "some comment", "text": ".= 1000; some comment"}
    """

    pseudo_comm_name = pp.Combine(
        pp.Literal(".")
        + (pp.Suppress(pp.Optional(" ")) + (pp.Literal("=")) | pp.Word(pp.alphas))
    )("pseudo")

    variable_name = pp.Combine(
        pp.Char(pp.alphas) + pp.Optional(pp.Word(pp.alphas + pp.nums + "_"))
    )("variable")
    variable_module = variable_name + pp.Suppress("=")
    label_name = variable_name("label") + pp.Suppress(":")

    argument_name = pp.Word(pp.printables, excludeChars=",;")
    full_argument_name = argument_name + pp.ZeroOrMore(pp.Suppress(",") + argument_name)

    command_name = variable_module | pseudo_comm_name | pp.Word(pp.alphas)("name")
    command_module = (
        command_name
        + pp.Optional(full_argument_name)("arg")
        + pp.Optional(pp.Suppress(";"))
    )

    comment_name = pp.Regex(r".+$")
    comment_module = comment_name("comm")

    full_parse_module = (
        pp.Optional(label_name)
        + pp.Optional(command_module)
        + pp.Optional(comment_module)
    )

    result = full_parse_module.parseString(text).as_dict()
    if not result.get("arg") and not result.get("label"):
        result["arg"] = []

    result["text"] = text

    return result


def recognize_args(args: list[str]) -> list[dict]:
    """
    Принимает список имен аргументов
    Возвращает для каждого отдельного аргумента
    словарь с нумером моды и именем аргумента по порядку.
    :param  args: список аргументов
        '['#2', 'R0']'
    :return:
        [{'mode': ['2'], 'const': '2'}, {'mode': ['0'], 'reg': 'R0'}]
    """

    res = []
    # Регистры Rn
    register_name = pp.Regex(
        r"""(([rR]+[0-7]))|(pc) | (PC)|(sp) | (SP)""", flags=VERBOSE
    )
    # Символы ASCII
    symbol_name = "'" + pp.Word(pp.printables)
    # Константы
    const_name = pp.Optional("-") + pp.Word(pp.nums) + pp.Optional(".")
    # Переменные и/или метки
    variable_name = pp.Combine(
        pp.Char(pp.alphas) + pp.Optional(pp.Word(pp.alphas + pp.nums + "_"))
    )
    # Общий модуль для констант
    const_var_name = symbol_name | const_name | variable_name
    # Сдвиги
    shift_name = pp.Combine(pp.Optional("-") + pp.Word(pp.nums))

    # Шаблоны для определения моды
    modes_list = [
        ("@" + shift_name + "(" + register_name + ")").setParseAction(
            pp.replaceWith("7")
        ),
        (shift_name + "(" + register_name + ")").setParseAction(pp.replaceWith("6")),
        ("#" + const_var_name).setParseAction(pp.replaceWith("2")),
        ("@#" + const_var_name).setParseAction(pp.replaceWith("3")),
        ("@" + const_var_name).setParseAction(pp.replaceWith("7")),
        ("@-(" + register_name + ")").setParseAction(pp.replaceWith("5")),
        ("-(" + register_name + ")").setParseAction(pp.replaceWith("4")),
        ("@(" + register_name + ")+").setParseAction(pp.replaceWith("3")),
        ("(" + register_name + ")+").setParseAction(pp.replaceWith("2")),
        ("(" + register_name + ")").setParseAction(pp.replaceWith("1")),
        register_name.setParseAction(pp.replaceWith("0")),
        const_var_name.setParseAction(pp.replaceWith("6")),
    ]

    modes_to_search = pp.MatchFirst(modes_list)("mode")

    # Опредение "имени" аргумента

    register_name = pp.Regex(
        r"""(([rR]+[0-7]))|(pc) | (PC)|(sp) | (SP)""", flags=VERBOSE
    )("reg")

    full_reg_name = (
        pp.Optional(pp.Suppress(pp.Word("@-+(")))
        + register_name
        + pp.Optional(pp.Suppress(pp.Word("+)")))
    )

    mode_6 = shift_name("shift") + pp.Suppress("(") + register_name + pp.Suppress(")")

    mode_7 = pp.Suppress("@") + mode_6

    # Символы ASCII
    symbol_name = "'" + pp.Word(pp.printables)("symbol")
    # Константы
    const_name = pp.Combine(pp.Optional("-") + pp.Word(pp.nums) + pp.Optional("."))
    # Переменные и/или метки
    variable_name = pp.Combine(
        pp.Char(pp.alphas) + pp.Optional(pp.Word(pp.alphas + pp.nums + "_"))
    )
    # Общий модуль для констант
    const_var_name = pp.Suppress(pp.Optional("@") + pp.Optional("#")) + (
        symbol_name | const_name("const") | variable_name("variable")
    )

    names_to_search = mode_7 | mode_6 | full_reg_name | const_var_name

    # Перебираем аргументы из args
    for arg in args:
        val_name = names_to_search.parseString(arg).as_dict()
        val_mode = modes_to_search.parseString(arg).as_dict()
        res.append({**val_mode, **val_name})
    return res


def code_arg(arg_dict: dict) -> str:
    """
    Принимает словарь с ключами 'mode' и 'reg'|'const'|'symbol'
    Возвращает кодировку для аргумента
    :param  arg_dict: словарь характеристик аргумента
        {'mode': ['2'], 'const': '2'}
    :return:
        '010111'
    """

    spec_reg_pc = pp.Regex(r"(pc) | (PC)", flags=VERBOSE)
    spec_reg_sp = pp.Regex(r"(sp) | (SP)", flags=VERBOSE)
    register_name = (
        pp.Suppress(pp.Literal("r") | pp.Literal("R")) + pp.Word("01234567")
        | spec_reg_pc
        | spec_reg_sp
    )

    spec_regs = [
        spec_reg_sp.setParseAction(pp.replaceWith("6")),
        spec_reg_pc.setParseAction(pp.replaceWith("7")),
        register_name,
    ]
    spec_to_search = pp.MatchFirst(spec_regs)

    mode_code = f"{int(arg_dict['mode'][0]):03b}"

    if arg_dict.get("const") or arg_dict.get("symbol"):
        name_code = f"{7:03b}"
    elif arg_dict.get("reg"):
        name_code = f"{int(spec_to_search.parse_string(arg_dict['reg'])[0]):03b}"
    # Заполнитель для необработанной переменной
    elif arg_dict.get("variable"):
        return "0" * 6

    return mode_code + name_code


def get_ascii_text(name: str, text: str) -> str:
    """
    Выделяет из строки аргумент для команды name,
    который представляес собой строку текста с одинаковым первым и последним символом
    Барьерный символ может быть любым (кроме пробела)
    :param name: имя команды
    :param text: текст для поиска
    """

    # Аргумент ищем после команды
    start = text.find(name) + len(name)
    # Выражение для поиска
    # Здесь (.) - один символ, который запомнили
    # (.*?) - символы между
    # \1 - на конце первый, который запомнили
    same_char_string = pp.Regex(r"(.)(.*?)\1")("string")
    # Область поиска
    text_to_search = text[start:]

    result = same_char_string.parseString(text_to_search)[0]
    # Барьерные символы игнорируются
    return result[1:-1]
