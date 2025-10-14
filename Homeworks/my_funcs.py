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
    command_name = pp.Word(pp.alphas) | pp.Keyword(". =")('pseudo')
    lable_name = pp.Word(pp.alphas)('lable')+pp.Suppress(':')

    argument_name = pp.Word(pp.alphanums + '()@#\'')
    comment_name = pp.Regex(r".+$")

    full_argument_name = argument_name + \
        pp.Optional(pp.Suppress(','+pp.empty) + argument_name)

    parse_module = command_name('name') +\
        pp.Optional(full_argument_name)('arg') +\
        pp.Optional(pp.Suppress(';')) +\
        pp.Optional(comment_name)('comm')

    full_parse_module = lable_name | parse_module

    result = full_parse_module.parseString(text).as_dict()
    if not result.get('arg') and not result.get('lable'):
        result['arg'] = []
    result['text'] = text.strip()
    return result


def recgnz_args(args: list[str]):
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
    const_name = pp.Word(pp.nums)
    # + символы ASCII
    simb_name = "\'" + pp.Word(pp.printables)("simb")
    # имя метки
    lable_name = pp.Word(pp.alphas)('lable')

    # для определения моды mmm
    modes_list = [
        ("@" + pp.Literal(pp.nums) + "(" + register_name +
         ")").setParseAction(pp.replaceWith('7')),
        (pp.Literal(pp.nums) + "(" + register_name +
         ")").setParseAction(pp.replaceWith('6')),
        ("#" + const_name).setParseAction(pp.replaceWith('2')),
        ("@#" + const_name).setParseAction(pp.replaceWith('3')),
        ("@" + const_name).setParseAction(pp.replaceWith('7')),
        const_name.setParseAction(pp.replaceWith('6')),
        ("@-(" + register_name + ")").setParseAction(pp.replaceWith('5')),
        ("-(" + register_name + ")").setParseAction(pp.replaceWith('4')),
        ("@(" + register_name + ")+").setParseAction(pp.replaceWith('3')),
        ("(" + register_name + ")+").setParseAction(pp.replaceWith('2')),
        ("(" + register_name + ")").setParseAction(pp.replaceWith('1')),
        register_name.setParseAction(pp.replaceWith('0')),
        lable_name.setParseAction(pp.replaceWith('lable'))
    ]

    modes_to_search = pp.MatchFirst(modes_list)('mode')

    # для определения имени аргумента rrr

    register_name = pp.Regex(
        r"""(([rR]+[0-7]))|(pc) | (PC)|(sp) | (SP)""", flags=VERBOSE)("reg")

    full_reg_name = pp.Optional(pp.Suppress(pp.Word('@-+('))) +\
        register_name +\
        pp.Optional(pp.Suppress(pp.Word('+)')))

    const_name = pp.Suppress(pp.Optional(pp.Word('#@'))
                             ) + pp.Word(pp.nums)("const")

    mode_6 = pp.Word(pp.nums)('shift') +\
        pp.Suppress("(") + register_name + pp.Suppress(")")

    mode_7 = pp.Suppress('@') + mode_6

    lable_name = pp.Word(pp.alphas)('lable')

    names_to_search = mode_7 | mode_6 | full_reg_name | simb_name | const_name | lable_name

    # перебираем каждый аргумент
    for arg in args:
        val_name = names_to_search.parseString(arg).as_dict()
        val_mode = modes_to_search.parseString(arg).as_dict()
        res.append({**val_mode, **val_name})

    return res


def recgnz_comm(text: str) -> str:
    """
    Принимает строку с именем команды
    Возвращает для начало кодировки команды
    :param  text: имя команды 
        'mov'
    :return: 
        '0001'
    """

    comms_list = [
        pp.Keyword(". =").setParseAction(pp.replaceWith('')),
        pp.Regex(r"(mov) | (MOV)", flags=VERBOSE).setParseAction(
            pp.replaceWith('0001')),
        pp.Regex(r"(movb) | (MOVB)", flags=VERBOSE).setParseAction(
            pp.replaceWith('1001')),
        pp.Regex(r"(add) | (ADD)", flags=VERBOSE).setParseAction(
            pp.replaceWith('0110')),
        pp.Regex(r"(sob) | (SOB)", flags=VERBOSE).setParseAction(
            pp.replaceWith('0111111')),
        pp.Regex(r"(halt) | (HALT)", flags=VERBOSE).setParseAction(
            pp.replaceWith('0'*16))
    ]

    comms_to_search = pp.MatchFirst(comms_list)

    return comms_to_search.parse_string(text)[0]


def code_arg(arg_dict: dict) -> str:
    """
    Принимает словарь с ключами 'mode' и 'reg'|'const'|'simb'
    Возвращает кодировку для аргумента
    :param  arg_dict: словарь характеристик аргумента 
        {'mode': ['2'], 'const': '2'}
    :return: 
        '010111'
    """
    if arg_dict.get('lable'):
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
    if 'const' in arg_dict.keys():
        name_code = f"{7:03b}"
    elif 'reg' in arg_dict.keys():
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
    if arg.get('lable'):
        return '', False
    mode = int(arg['mode'][0])
    if arg.get('reg'):
        pass
    if arg.get('const'):
        if mode == 2:
            return f'{int(arg['const']):016b}', True
    return '', False


def bin_to_oct(text: str):
    """
    Принимает строку с двоичным 16-бит числом
    Возвращает число, где первый символ совпадает с первоым символом text,
    а все последующие являются восьмеричным представлением соответствующий трёх двоичных битов.
    :param  text: 16-битная строка 
        '0001010111000000'
    :return: 
        '012700'
    """
    if text == '':
        return ''
    res = text[0] + ''.join(
        [f"{int(text[i-3:i], 2):o}" for i in range(len(text), 1, -3)])[::-1]
    return f"{int(res):06}"
