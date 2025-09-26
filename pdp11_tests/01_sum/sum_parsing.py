from my_funcs import parse_command, recognize_command, \
    get_mode_reg_from_args, get_oct_from_bin

commands = []
programm_counter = f'{0:06}'

with open(r'pdp11_tests\01_sum\01_sum.pdp') as file:
    while True:
        str_ = file.readline()
        if str_:
            str_dict = parse_command(str_).as_dict()
            commands.append(programm_counter + ':\t' + str_.rstrip() + '\n')

            if str_dict['name'] == '. =':
                programm_counter = f"{(int(programm_counter, 8) +
                                       int(str_dict['arg'][0], 8)):06o}"
                continue

            name = recognize_command(str_dict['name'])
            args = get_mode_reg_from_args(
                str_dict['arg']) if "arg" in str_dict.keys() else ['']

            commands.append(
                '\t' + get_oct_from_bin(name[0] + ''.join(args))+"\n")
            programm_counter = f"{(int(programm_counter, 8) + 2):06o}"

            # заглушка для констант вида #*
            if "arg" in str_dict.keys():
                for arg in str_dict['arg']:
                    if arg[0] not in "rRpPSs":
                        commands.append('\t' + f'{int(arg[1:]):06o}'+"\n")
                        programm_counter = f"{(int(programm_counter, 8) + 2):06o}"
        else:
            commands.append(programm_counter + ':\t')
            break

with open(r'pdp11_tests\01_sum\01_sum.txt', mode='a') as file:
    for str_ in commands:
        file.write(str_)
