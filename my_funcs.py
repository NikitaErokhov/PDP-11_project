import pyparsing as pp
from re import VERBOSE


def parse_line(text: str):
    """
    Принимает строку с командой
    Возвращает саму строку, а также выделенное имя команды, аргументы и комментарий
    :param  text: строка с командой
        'mov 	#2, R0;'
    :return:
        {'name': 'mov', 'arg': ['#2', 'R0'], 'text': 'mov \t#2, R0;'}
    """

    pseudo_comm_name = pp.Combine(pp.Literal(".") + (pp.Suppress(pp.Optional(' ')) + (pp.Literal('=')) | pp.Word(pp.alphas)))('pseudo')
    
    variable_name = pp.Combine(pp.Char(pp.alphas) + pp.Optional(pp.Word(pp.alphas + pp.nums + "_")))('variable')

    variable_module = variable_name + pp.Suppress('=')

    command_name = variable_module| pseudo_comm_name | pp.Word(pp.alphas)('name')

    label_name = variable_name('label')+pp.Suppress(':')

    argument_name = pp.Word(pp.printables, excludeChars=',;')

    comment_name = pp.Regex(r".+$")

    full_argument_name = (argument_name + \
        pp.ZeroOrMore(pp.Suppress(',') + argument_name))

    command_module = (command_name +\
        pp.Optional(full_argument_name)('arg') +\
        pp.Optional(pp.Suppress(';')))

    comment_module = comment_name('comm')

    full_parse_module = pp.Optional(
        label_name) + pp.Optional(command_module) + pp.Optional(comment_module)

    result = full_parse_module.parseString(text).as_dict()
    if not result.get('arg') and not result.get('label'):
        result['arg'] = []

    result['text'] = text

    return result


def recognize_args(args: list[str]):
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
    # Регистр Rn
    register_name = pp.Regex(
        r"""(([rR]+[0-7]))|(pc) | (PC)|(sp) | (SP)""", flags=VERBOSE)
    # константа #n
    const_name = pp.Optional('-') + pp.Word(pp.alphanums)
    # + символы ASCII
    symbol_name = "#\'" + pp.Word(pp.printables)("symbol")
    # имя метки
    label_name = pp.Combine(
        pp.Char(pp.alphas) + pp.Optional(pp.Word(pp.alphas + pp.nums + "_")))('label')

    # для определения моды mmm
    modes_list = [
        ("@" + pp.Literal(pp.nums) + "(" + register_name +
         ")").setParseAction(pp.replaceWith('7')),
        (pp.Literal(pp.nums) + "(" + register_name +
         ")").setParseAction(pp.replaceWith('6')),
        ("#" + const_name).setParseAction(pp.replaceWith('2')),
        ("@#" + const_name).setParseAction(pp.replaceWith('3')),
        ("@" + const_name).setParseAction(pp.replaceWith('7')),
        ("@-(" + register_name + ")").setParseAction(pp.replaceWith('5')),
        ("-(" + register_name + ")").setParseAction(pp.replaceWith('4')),
        ("@(" + register_name + ")+").setParseAction(pp.replaceWith('3')),
        ("(" + register_name + ")+").setParseAction(pp.replaceWith('2')),
        ("(" + register_name + ")").setParseAction(pp.replaceWith('1')),
        register_name.setParseAction(pp.replaceWith('0')),
        label_name.setParseAction(pp.replaceWith('-')),
        const_name.setParseAction(pp.replaceWith('6')),
        symbol_name.setParseAction(pp.replaceWith('2'))
    ]

    modes_to_search = pp.MatchFirst(modes_list)('mode')

    # для определения имени аргумента rrr

    register_name = pp.Regex(
        r"""(([rR]+[0-7]))|(pc) | (PC)|(sp) | (SP)""", flags=VERBOSE)("reg")

    full_reg_name = pp.Optional(pp.Suppress(pp.Word('@-+('))) +\
        register_name +\
        pp.Optional(pp.Suppress(pp.Word('+)')))

    mode_6 = pp.Word(pp.nums)('shift') +\
        pp.Suppress("(") + register_name + pp.Suppress(")")

    mode_7 = pp.Suppress('@') + mode_6

    label_name = pp.Combine(
        pp.Char(pp.alphas) + pp.Optional(pp.Word(pp.alphas + pp.nums + "_")))('label')

    const_name = pp.Suppress(pp.Optional(pp.Word('#@'))
                             ) + (pp.Combine(pp.Optional('-') + pp.Word(pp.nums))("const") | label_name('variable'))
    
    symbol_name = "#\'" + pp.Word(pp.printables)("symbol")

    names_to_search = mode_7 | mode_6 | full_reg_name | symbol_name | label_name | const_name | symbol_name

    # перебираем каждый аргумент
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
    if arg_dict.get('label') or arg_dict.get('variable'):
        return ''

    spec_reg_pc = pp.Regex(r"(pc) | (PC)", flags=VERBOSE)
    spec_reg_sp = pp.Regex(r"(sp) | (SP)", flags=VERBOSE)
    register_name = pp.Suppress(pp.Literal('r') | pp.Literal('R')) + \
        pp.Word("01234567") | spec_reg_pc | spec_reg_sp

    spec_regs = [
        spec_reg_sp.setParseAction(pp.replaceWith('6')),
        spec_reg_pc.setParseAction(pp.replaceWith('7')),
        register_name
    ]

    spec_to_search = pp.MatchFirst(spec_regs)

    mode_code = f"{int(arg_dict['mode'][0]):03b}"

    if arg_dict.get("const"):
        name_code = f"{7:03b}"
    elif arg_dict.get("symbol"):
        name_code = f"{7:03b}"
    elif arg_dict.get("reg"):
        name_code = f"{int(spec_to_search.parse_string(arg_dict['reg'])[0]):03b}"

    return mode_code + name_code


def recgnz_mode(arg: dict):
    """
    Принимает словарь с ключами 'mode' и 'reg'|'const'|'simb'
    Возвращает если необходимо восьмеричные данные,
    необходимые для реализации специфичной моды
    Для моды 2 регистра R7 вернет восьмеричное представление константы
    :param  arg: словарь характеристик аргумента
        {'mode': ['2'], 'const': '2'}
    :return:
        '000002'
    """
    if arg.get('label') or arg.get('reg'):
        return '', False

    if arg.get('const'):
        number = int(arg['const'], 8)
        width = 16
        result = f'{abs(number):0{width}b}'

        if number < 0:
            number_unsigned = (1 << width) + number
            result = f'{number_unsigned:{width}b}'

        return result, True
    
    elif arg.get('symbol'):
        return f'{(ord(arg['symbol'])):016b}', True

    elif arg.get('variable'):
        # Для прекомпиляции когда все переменные могут быть до конца неизвестны
        return f'{0:016b}', True
    return '', False


def get_ascii_text(name: str, text: str):

    start = text.find(name) + len(name)

    same_char_string = pp.Regex(r'(.)(.*?)\1')('string')

    text_to_search = text[start:]

    result = same_char_string.parseString(text_to_search)
    
    return result[0][1:-1]
