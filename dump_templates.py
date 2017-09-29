from pyzabbix import ZabbixAPI
import time
import sys

###Necessary variables###
tab = '\t|\t'
calc_fnc_list = ['','min','avg','','max','','','all','','']
graphtype_list = ['Normal', 'Stacked', 'Pie', 'Exploded']
value_type_list = ['Numeric (float)','Character','Log','Numeric (unsigned)','Text']
length_dict = {'macro_name':0, 'item_name':0, 'item_key':0, 'item_type':0, 'trigger_desc':0, 'trigger_expr':0, 'graph_name':0}
#########################

def parse_args_and_connect_to_zabbix(args):
	try:
		zabbix_host = args[args.index('-h'):][1]
		zabbix_user = args[args.index('-u'):][1]
		zabbix_password = args[args.index('-p'):][1]
		output_file = args[args.index('-o'):][1]
		if 'http://' not in zabbix_host:
			zabbix_host = 'https://' + zabbix_host
		zabbix = ZabbixAPI(zabbix_host, user=zabbix_user, password=zabbix_password)
	except:
		print('Unable to connect to zabbix with provided data or misspelling with provided options\nPlease, try to connect again with specified options -h <Zabbix hostname/IP address> -u <Zabbix username>\
 -p <Zabbix user password> -o <Outputfile>')
	else:
		return(zabbix,output_file)

def tabs(length_dict, input_dict, char, length_dict_field, input_dict_field): # Calculate how many tabs are necessary for given field to make output straight
	num = length_dict[length_dict_field]/8 - len(input_dict[input_dict_field])/8 + 1
	return('\t'*num+char+'\t')

def extract_params_from_key(item): # Some items consist of variables like $3, $4 which are parameters position for key.
								   # To make item name more human readable it will replace such variables with corresponding parameters
								   # Macros will not be replaced
	name = item['name'].split(' ')
	for word in name:
		try:
			word.index('$')
		except:
			False
		else:
			num = word[word.index('$'):word.index('$') + 2]
			if num in ['$' + str(i) for i in range(10)]:
				value_to_replace = item['key_'].split('[')[1][:-1].split(',')[int(num[1]) - 1]
			else:
				value_to_replace = num
			name[name.index(word)] = word[:word.index('$')] + value_to_replace + word[word.index('$') + 2:]
	return(' '.join(name))

def calculate_expression(trigger,items):
	list_of_expr = []
	functions = trigger['functions']
	expression = trigger['expression']
	beg = expression.index('{')
	end = expression.index('}')
	while '{' in expression[beg:] and '}' in expression[end:]:
		functionid = expression[beg + 1:end]
		try:
			int(functionid)
		except:
			beg = beg + 1
			end = end + 1
		else:
			for function in functions:
				if functionid == function['functionid']:
					for item in items:
						if function['itemid'] == item['itemid']:
							list_of_expr.append(
								item['key_'] + '.' + function['function'] + '(' + function['parameter'] + ')')
							break
			expression = expression[:beg + 1] + expression[end:]
		try:
			beg = expression.index('{', beg + 1)
			end = expression.index('}', end + 2)
		except:
			False
	for expr in list_of_expr:
		expression = expression.replace('{}', '{' + expr + '}', 1)
	return(expression)

def calc_max_len_from_2dray(input_dict,field): # Find the longest value for key with name field across list of list of dictionaries
	return(max([max([len(input_dict[j][i][field]) for i in range(len(input_dict[j]))]) for j in range(len(input_dict))]))

def calc_max_len_from_1dray(input_dict,field): # Find the longest value for key with name field across list of dictionaries
	try:
		max_len = max([len(i[field]) for i in input_dict])
	except:
		return(0)
	else:
		return(max_len)

def main(z,output_file):
	#templates = z.template.get(templateids='12196') # To make dump for one template specify hostid for your template
	templates = z.template.get(groupids=['95','1','8']) #I am interested to dump zabbix templates information only from specified groups

	f = open(output_file,'a')
	for template in templates:
		hostid = template['templateid']

		f.write(''.join(['#' for i in range(len(template['host']))])+'\n'+template['host']+'\n'+''.join(['#' for i in range(len(template['host']))]) + '\n')
		f.write('######\nMACROS\n######\n')
		macros = z.usermacro.get(hostids=hostid)
		length_dict['macro_name'] = calc_max_len_from_1dray(macros,'macro')
		for macro in macros:
			f.write(macro['macro']+tabs(length_dict,macro,'=>','macro_name','macro')+macro['value'] + '\n')

		f.write('#####\nITEMS\n#####\n')
		items = sorted(z.item.get(hostids=hostid), key=lambda x: x['name'].lower()) # Order items by name
		for item in items:
			if item['status'] == '0':
				item['value_type'] = value_type_list[int(item['value_type'])] # Replace all digits of value_type with human readable values like Text, Log, Character, etc
				if item['params'] != '' and item['itemid'] != '27753': # Strange information at database only for item with itemid 27753
					item['key_'] = item['params']
				item['name'] = extract_params_from_key(item)

		length_dict['item_name'] = calc_max_len_from_1dray(items,'name')
		length_dict['item_key'] = calc_max_len_from_1dray(items,'key_')
		length_dict['item_type'] = calc_max_len_from_1dray(items,'value_type')

		for item in items:
			if item['status'] == '0':
				f.write((item['name'] + tabs(length_dict,item,'|','item_name','name') \
						 + item['key_'] + tabs(length_dict,item,'|','item_key','key_')\
						 + item['value_type'] + tabs(length_dict,item,'|','item_type','value_type')\
						 + item['delay'] + tab + item['history'] + '\n').encode('utf-8'))
		f.write('###############\nITEM_PROTOTYPES\n###############\n')
		item_prototypes = sorted(z.itemprototype.get(hostids=hostid), key=lambda x: x['name'].lower()) # Order items by name
		for item_prototype in item_prototypes:
			if item_prototype['status'] == '0':
				item_prototype['value_type'] = value_type_list[int(item_prototype['value_type'])]  # Replace all values digits with human readable values like Text, Log, Character, etc
				if item_prototype['params'] != '':
					item_prototype['key_'] = item_prototype['params'] # Replace key_ field with params at database for calculated items
				item_prototype['name'] = extract_params_from_key(item_prototype) # Calculate expression for trigger. It will transform expression from {13228}<1024 to {kernel.maxfiles.last(0)}<1024

		length_dict['item_name'] = calc_max_len_from_1dray(item_prototypes,'name')
		length_dict['item_key'] = calc_max_len_from_1dray(item_prototypes,'key_')
		length_dict['item_type'] = calc_max_len_from_1dray(item_prototypes,'value_type')

		for item_prototype in item_prototypes:
			if item_prototype['status'] == '0':
				f.write((item_prototype['name'] + tabs(length_dict,item_prototype,'|','item_name','name') + item_prototype['key_'] \
						 + tabs(length_dict,item_prototype,'|','item_key','key_') + item_prototype['value_type']\
						 + tabs(length_dict,item_prototype,'|','item_type','value_type') + item_prototype['delay']\
						 + tab + item_prototype['history'] + '\n').encode('utf-8'))
		f.write('########\nTRIGGERS\n########\n')
		triggers = sorted(z.trigger.get(hostids=hostid,selectFunctions='extend'),key=lambda x: x['priority']+x['description']) # Order triggers by priority + description
		for trigger in triggers:
			if trigger['status'] == '0':
				trigger['expression'] = calculate_expression(trigger, items)

		length_dict['trigger_desc'] = calc_max_len_from_1dray(triggers,'description')
		length_dict['trigger_expr'] = calc_max_len_from_1dray(triggers,'expression')

		for trigger in triggers:
			if trigger['status'] == '0':
				f.write((trigger['description'] + tabs(length_dict,trigger,'|','trigger_desc','description') + trigger['expression']\
						 + tabs(length_dict,trigger,'|','trigger_expr','expression') + trigger['priority']+'\n').encode('utf-8'))
		f.write('##################\nTRIGGER_PROTOTYPES\n##################\n')
		trigger_prototypes = sorted(z.triggerprototype.get(hostids=hostid,selectFunctions='extend'),key=lambda x: x['priority']+x['description'])
		for trigger_prototype in trigger_prototypes:
			if trigger_prototype['status'] == '0':
				trigger_prototype['expression'] = calculate_expression(trigger_prototype, item_prototypes)

		length_dict['trigger_desc'] = calc_max_len_from_1dray(trigger_prototypes,'description')
		length_dict['trigger_expr'] = calc_max_len_from_1dray(trigger_prototypes,'expression')

		for trigger_prototype in trigger_prototypes:
			if trigger_prototype['status'] == '0':
				f.write((trigger_prototype['description'] + tabs(length_dict,trigger_prototype,'|','trigger_desc','description')\
						 + trigger_prototype['expression'] + tabs(length_dict,trigger_prototype,'|','trigger_expr','expression')\
						 + trigger_prototype['priority'] + '\n').encode('utf-8'))
		f.write('######\nGRAPHS\n######\n')

		graphs = sorted(z.graph.get(hostids=hostid,selectGraphItems='extend'),key=lambda x: x['name'].lower())

		for graph in graphs:
			graph['graphtype'] = graphtype_list[int(graph['graphtype'])]
			for graphitem in graph['gitems']:
				for item in items:
					if graphitem['itemid'] == item['itemid']:
						graphitem['name'] = item['name']
				graphitem['calc_fnc'] = calc_fnc_list[int(graphitem['calc_fnc'])]
			if calc_max_len_from_1dray(graph['gitems'],'name') > length_dict['graph_name']:
				length_dict['graph_name'] = calc_max_len_from_1dray(graph['gitems'],'name')

		if calc_max_len_from_1dray(graphs,'name') > length_dict['graph_name']:
			length_dict['graph_name'] = calc_max_len_from_1dray(graphs, 'name')

		for graph in graphs:
			f.write(graph['name'] + tabs(length_dict,graph,'|','graph_name','name') + graph['graphtype'] + '\n' + '#GRAPH_ITEMS\n')
			graphitems = sorted(graph['gitems'], key=lambda x: x['sortorder'])
			for graphitem in graphitems:
					f.write((graphitem['name'] + tabs(length_dict,graphitem,'|','graph_name','name') + graphitem['calc_fnc'] + '\n').encode('utf-8'))
			f.write('###################\n')
		f.write('################\nGRAPH_PROTOTYPES\n################\n')

		graph_prototypes = sorted(z.graphprototype.get(hostids=hostid, selectGraphItems='extend'), key=lambda x: x['name'].lower())
		for graph_prototype in graph_prototypes:
			graph_prototype['graphtype'] = graphtype_list[int(graph_prototype['graphtype'])]
			for graph_prototype_item in graph_prototype['gitems']:
				for item_prototype in item_prototypes:
					if graph_prototype_item['itemid'] == item_prototype['itemid']:
						graph_prototype_item['name'] = item_prototype['name']
				graph_prototype_item['calc_fnc'] = calc_fnc_list[int(graph_prototype_item['calc_fnc'])]
			if calc_max_len_from_1dray(graph_prototype['gitems'],'name') > length_dict['graph_name']:
				length_dict['graph_name'] = calc_max_len_from_1dray(graph_prototype['gitems'], 'name')

		for	graph_prototype in graph_prototypes:
			f.write((graph_prototype['name'] + tabs(length_dict,graph_prototype,'|','graph_name','name') + graph_prototype['graphtype'] + '\n').encode('utf-8'))
			graph_prototype_items = sorted(graph_prototype['gitems'], key=lambda x: x['sortorder'])
			for graph_prototype_item in graph_prototype_items:
					f.write((graph_prototype_item['name'] + tabs(length_dict,graph_prototype_item,'|','graph_name','name') + graph_prototype_item['calc_fnc'] + '\n').encode('utf-8'))
			f.write('###################\n')
		time.sleep(5) #Adjustable delay to not overhead your database
	f.close()

if __name__ == "__main__":
	zabbix, output_file = parse_args_and_connect_to_zabbix(sys.argv[1:])
	main(zabbix, output_file)