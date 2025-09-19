import pyparsing as pp

args = ['(R3)+', '(R2)', '(R1)']


def get_mode_reg_from_args(args: list[str]):
    binary_result = []
    argument_name = pp.Word(pp.alphanums)
    modes_list = [("(" + argument_name + ")+").setParseAction(pp.replaceWith(2)),
                  ("(" + argument_name + ")").setParseAction(pp.replaceWith(1)),
                  argument_name.setParseAction(pp.replaceWith(0)),
                  ]

    modes_to_search = pp.MatchFirst(modes_list)
    register_name = pp.Optional(pp.Suppress('('))+pp.Word("R01234567")

    for arg in args:
        reg_name = register_name.parseString(arg)[0]
        reg_mode = modes_to_search.parseString(arg)[0]
        binary_result.append(f"{reg_mode:03b}{int(reg_name[1]):03b}")

    print(binary_result)


get_mode_reg_from_args(args)
