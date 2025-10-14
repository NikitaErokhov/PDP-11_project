import pyparsing as pp


def parse_command(text: str):

    command_name = pp.Word(pp.alphas)('name')
    argument_name = pp.Word(pp.alphanums + '#()+-@')
    comment_name = pp.Regex(r".+$")

    full_argument_name = argument_name + \
        pp.Optional(pp.Suppress(','+pp.empty) + argument_name)

    parse_module = command_name + \
        pp.Optional(full_argument_name)('arg') + \
        pp.Suppress(';') + \
        pp.Optional(comment_name)('comm')

    return parse_module.parseString(text)


def print_dict(dict_: dict):
    for item in dict_.items():
        if not isinstance(item[1], list):
            print(f"{item[0]}: {item[1]}")
        else:
            i = 0
            for key in item[1]:
                print(f"{item[0]}{i}: {key}")
                i += 1
