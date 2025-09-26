import pyparsing as pp
from re import VERBOSE


def get_mode_reg_from_args(args: list[str]):

    result = []
    argument_name = pp.Word(
        pp.alphanums+'#')

    spec_argument_name = pp.Word(
        pp.alphanums+'#') | "\'" + pp.Word(pp.printables)
    modes_list = [
        ("@2(" + argument_name + ")").setParseAction(pp.replaceWith(7)),
        ("2(" + argument_name + ")").setParseAction(pp.replaceWith(6)),
        ("#" + pp.Word(pp.nums)).setParseAction(pp.replaceWith(2)),
        ("@#" + pp.Word(pp.nums)
         ).setParseAction(pp.replaceWith(3)),
        ("@" + pp.Word(pp.nums)).setParseAction(pp.replaceWith(7)),
        pp.Word(pp.nums).setParseAction(pp.replaceWith(6)),
        ("@-(" + argument_name + ")").setParseAction(pp.replaceWith(5)),
        ("-(" + argument_name + ")").setParseAction(pp.replaceWith(4)),
        ("@(" + argument_name + ")+").setParseAction(pp.replaceWith(3)),
        ("(" + argument_name + ")+").setParseAction(pp.replaceWith(2)),
        ("(" + argument_name + ")").setParseAction(pp.replaceWith(1)),
        spec_argument_name.setParseAction(pp.replaceWith(0)),
    ]

    modes_to_search = pp.MatchFirst(modes_list)

    register_name = pp.Optional(pp.Suppress(
        pp.Word('@2-+('))) + pp.Regex(r"""
                (([rR]+[0-7]))
                |
                (pc) | (PC)
                |
                (sp) | (SP)""", flags=VERBOSE) +\
        pp.Optional(pp.Suppress(pp.Word('+)')))

    const_name = pp.Optional(pp.Suppress(pp.Word('#@'))) + \
        pp.Word(pp.nums)

    simb_name = "\'" + pp.Word(pp.printables)

    # value_name = register_name | const_name | simb_name

    names_list = [
        const_name.setParseAction(pp.replaceWith('R7')),
        simb_name,
        register_name
    ]

    names_to_search = pp.MatchFirst(names_list)

    for arg in args:
        val_mode = modes_to_search.parseString(arg)[0]
        val_name = names_to_search.parseString(arg)
        result.append(f"{int(val_mode):03b}" +
                      recognize_reg(''.join(val_name)))

    return result


def parse_command(text: str):

    command_name = pp.Word(pp.alphas) | pp.Keyword(". =")
    argument_name = pp.Word(pp.alphanums + '()@#\'')
    comment_name = pp.Regex(r".+$")

    full_argument_name = argument_name + \
        pp.Optional(pp.Suppress(','+pp.empty) + argument_name)

    parse_module = command_name('name') +\
        pp.Optional(full_argument_name)('arg') +\
        pp.Suppress(';') +\
        pp.Optional(comment_name)('comm')

    return parse_module.parseString(text)


def recognize_command(text: str):
    comms_list = [
        pp.Keyword(". =").setParseAction(pp.replaceWith('')),
        pp.Keyword("mov").setParseAction(pp.replaceWith('0001')),
        pp.Keyword("movb").setParseAction(pp.replaceWith('1001')),
        pp.Keyword("add").setParseAction(pp.replaceWith('0110')),
        pp.Keyword("halt").setParseAction(pp.replaceWith('0'*16))
    ]

    comms_to_search = pp.MatchFirst(comms_list)

    return comms_to_search.parse_string(text)


def recognize_reg(text: str):

    spec_reg_pc = pp.Regex(r"(pc) | (PC)", flags=VERBOSE)
    spec_reg_sp = pp.Regex(r"(sp) | (SP)", flags=VERBOSE)
    register_name = pp.Suppress(pp.Literal('r') | pp.Literal('R')) + \
        pp.Word("01234567") | spec_reg_pc | spec_reg_sp

    spec_regs = [
        spec_reg_sp.setParseAction(pp.replaceWith('6')),
        spec_reg_pc.setParseAction(pp.replaceWith('7')),
        register_name,
        pp.Word(pp.nums)
    ]

    spec_to_search = pp.MatchFirst(spec_regs)

    return f"{int(spec_to_search.parse_string(text)[0]):03b}"


def get_oct_from_bin(text: str):
    res = ''.join(
        [f"{int(text[i-3:i], 2):o}" for i in range(len(text), 1, -3)])[::-1]
    # for i in range(len(text), 1, -3):
    #     print(i, i-3, text[i-3:i])
    # print(res)
    return text[0]+res
