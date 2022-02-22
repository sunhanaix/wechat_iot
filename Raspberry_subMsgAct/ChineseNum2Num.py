'''
照搬的https://blog.csdn.net/xiamin/article/details/85550898上的汉字数字转数字部分的代码
就不自己造轮子了
'''
CN_NUM = {
    '〇': 0,
    '一': 1,
    '二': 2,
    '三': 3,
    '四': 4,
    '五': 5,
    '六': 6,
    '七': 7,
    '八': 8,
    '九': 9,
 
    '零': 0,
    '壹': 1,
    '贰': 2,
    '叁': 3,
    '肆': 4,
    '伍': 5,
    '陆': 6,
    '柒': 7,
    '捌': 8,
    '玖': 9,
 
    '貮': 2,
    '两': 2,
}
CN_UNIT = {
    '十': 10,
    '拾': 10,
    '百': 100,
    '佰': 100,
    '千': 1000,
    '仟': 1000,
    '万': 10000,
    '萬': 10000,
    '亿': 100000000,
    '億': 100000000,
    '兆': 1000000000000,
}
 
 
def cn2dig(cn):
    lcn = list(cn)
    unit = 0   # 当前的单位
    ldig = []  # 临时数组
 
    while lcn:
         cndig = lcn.pop()
         if  cndig in CN_UNIT:
            unit = CN_UNIT.get(cndig)
            if unit == 10000:
                ldig.append('w')  # 标示万位
                unit = 1
            elif unit == 100000000:
                ldig.append('y')  # 标示亿位
                unit = 1
            elif unit == 1000000000000:  # 标示兆位
                ldig.append('z')
                unit = 1
            continue
         else:
            dig = CN_NUM.get(cndig)
 
            if unit:
                dig = dig * unit
                unit = 0
 
            ldig.append(dig)
 
    if unit == 10:  # 处理10-19的数字
        ldig.append(10)
 
    ret = 0
    tmp = 0
 
    while ldig:
        x = ldig.pop()
 
        if x == 'w':
            tmp *= 10000
            ret += tmp
            tmp = 0
 
        elif x == 'y':
            tmp *= 100000000
            ret += tmp
            tmp = 0
 
        elif x == 'z':
            tmp *= 1000000000000
            ret += tmp
            tmp = 0
 
        else:
            tmp += x
 
    ret += tmp
    return ret

if __name__=='__main__':
    print(cn2dig(55))