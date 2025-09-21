import pyparsing as pp
from re import VERBOSE


def get_mode_reg_from_args(args: list[str], test: bool = False):

    result = dict()
    argument_name = pp.Word(pp.alphanums+'#')

    modes_list = [
        ("@2(" + argument_name + ")").setParseAction(pp.replaceWith(7)),
        ("2(" + argument_name + ")").setParseAction(pp.replaceWith(6)),
        ("#" + pp.Word(pp.nums)).setParseAction(pp.replaceWith("2 const")),
        ("@#" + pp.Word(pp.nums)
         ).setParseAction(pp.replaceWith("3 mem[mem[v]]")),
        ("@" + pp.Word(pp.nums)).setParseAction(pp.replaceWith("7 mem[v]")),
        pp.Word(pp.nums).setParseAction(pp.replaceWith("6 mem[v]")),
        ("@-(" + argument_name + ")").setParseAction(pp.replaceWith(5)),
        ("-(" + argument_name + ")").setParseAction(pp.replaceWith(4)),
        ("@(" + argument_name + ")+").setParseAction(pp.replaceWith(3)),
        ("(" + argument_name + ")+").setParseAction(pp.replaceWith(2)),
        ("(" + argument_name + ")").setParseAction(pp.replaceWith(1)),
        argument_name.setParseAction(pp.replaceWith(0)),
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

    value_name = register_name | const_name

    for arg in args:
        val_mode = modes_to_search.parseString(arg)[0]
        val_name = value_name.parseString(arg)[0]
        result[val_name.upper()] = val_mode
        if (test):
            print(f"from {arg} get mode {val_mode} for {val_name.upper()}")

    return result
