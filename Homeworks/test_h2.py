from arg_modes import get_mode_reg_from_args
from parsing_a_line import parse_command, print_dict


def space(text: str = ''):
    print('\n'+'-'*24+text+'-'*24+'\n')


def test(name: str = '', text: str = '', test: bool = False):
    space(name)
    res = parse_command(text).as_dict()
    arg_mode_dict = get_mode_reg_from_args(res['arg'], test=test)
    print_dict(arg_mode_dict)


def spec_R7_mult_test(test: bool = False):
    space('spec_R7_1_test')
    args = ['#3', '100.', '@4914', '@#555']
    get_mode_reg_from_args(args, test)


def spec_PC_SP_mult_test(test: bool = False):
    space('spec_PC_SP_mult_test')
    args = ['sp', '(SP)', '(pc)+', '-(PC)']
    get_mode_reg_from_args(args, test)


def spec_ASCII_mult_test(test: bool = False):
    space('spec_ASCII_mult_test')
    args = ['\'*', '\'a']
    get_mode_reg_from_args(args, test)


TEST = False

test('simple_test', 'add R0, R1;', TEST)
test('mode_1_test', 'inc (r2);', TEST)
test('mode_2_test', 'inc (pc)+;', TEST)
test('mode_3_test', 'inc @(R3)+;', TEST)
test('mode_4_test', 'inc -(r3);', TEST)
test('mode_5_test', 'inc @-(R3);', TEST)
test('mode_6_test', 'inc 2(r3);', TEST)
test('mode_7_test', 'inc @2(R3);', TEST)

spec_R7_mult_test(TEST)
spec_PC_SP_mult_test(TEST)
spec_ASCII_mult_test(TEST)


space('EVERYTHINK IS OK')
