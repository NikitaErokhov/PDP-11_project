from Homeworks.h1_parsing_a_line import parse_command, print_dict, pp


def space(text: str = ''):
    print('\n'+'-'*24+text+'-'*24+'\n')


def simple_test():
    space('simple_test')
    text = 'add R0, R1 ; сложение регистров R0 и R1, результат в R1'
    # text = 'add R0 R1 ;'

    print('text: '+text+'\n')
    res = parse_command(text)
    print(f'{res=}')


def print_test():
    space('print_test')
    text = 'add R0, R1 ; сложение регистров R0 и R1, результат в R1'
    print('text: '+text+'\n')
    res = parse_command(text).as_dict()
    print_dict(res)


def without_comment():
    space('without_comment')
    text = 'add R0, R1;'
    print('text: '+text+'\n')
    res = parse_command(text).as_dict()
    print_dict(res)


def without_args():
    space('without_args')
    text = 'exit ; comment'
    print('text: '+text+'\n')
    res = parse_command(text).as_dict()
    print_dict(res)


def without_args_comment():
    space('without_args_comment')
    text = 'exit ;'
    print('text: '+text+'\n')
    res = parse_command(text).as_dict()
    print_dict(res)


# def many_arguments():
#     space('many_arguments')
#     text = 'echo R0, R1, #2, @r9b, PriNtf() ; too many args'
#     print('text: '+text+'\n')
#     res = parse_command(text).as_dict()
#     print_dict(res)


def empty():
    space('empty')
    text = ''
    print('text: '+text+'\n')
    try:
        parse_command(text)
    except pp.exceptions.ParseException:
        print('Ошибка поймана - ожидал комманду, получил ничего')
        return
    print('не поймал ошибку')


def without_ending():
    space('without_ending')
    text = 'exit'
    print('text: '+text+'\n')
    try:
        parse_command(text)
    except pp.exceptions.ParseException:
        print('Ошибка поймана - ожидал ;')
        return
    print('не поймал ошибку')


simple_test()
print_test()
without_comment()
without_args()
without_args_comment()
# many_arguments()

empty()
without_ending()

space('EVERYTHINK IS OK')
