#!/usr/bin/python3

import os
import re
from io import BytesIO
from os.path import exists, dirname
from sys import stderr

import requests as rq
from fire import Fire, decorators
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageGrab import grabclipboard
from json import load

# global const
# 定义默认字体大小范围。文字最小不应小于font_min，最大不应大于font_max。
font_min = 14
font_max = 72

working_dir = "."
# 由命令行入口进入
CLI_Entrance = False
# 分隔符
global_delimiter = ','
# 错误代码表
error_code = {
    1: "图片不存在",
    2: "字号应为整数",
    3: "语种不存在",
    4: "语种对应的字体不存在",
    5: "缺少提示语",
    6: "缺少图片",
    7: "图片获取失败",
    8: "剪贴板中不包含图片",
    9: "输入的背景色格式不正确",
    10: "语种-字体对应表文件fonts.json有错误"
}
# 语种-字体对应表
font_dict = {}
try:
    with open("fonts.json", "r") as f:
        js = load(f)
    for i in js.keys():
        font_dict[i] = working_dir + os.sep + 'font' + os.sep + js[i]
except:
    stderr.write(error_code[10])

# aux functions


def CLParser(cl: str):
    global global_delimiter
    return cl.strip("\"\' ").split(global_delimiter)

# main object
@decorators.SetParseFn(CLParser)
class BHG(object):
    # private

    def __init__(self, *args, **kwargs):
        '''
        初始化。
        '''
        global CLI_Entrance

        self.clear()

        self.__succeed = (CLI_Entrance) and (
            self.CLIEntrance(*args, **kwargs) == 0)

    def __str__(self):
        if self.__succeed:
            return ''
        else:
            # Fire的--help等于print(self.__str__())
            return self.CLIEntrance.__doc__

    def __loadimg(self):
        '''
        读入路径为self.__setting['path']的原图并转换为黑白图片。
        '''
        if self.__setting['path'] == '~':
            # 说明读入剪贴板
            img = grabclipboard()
            if isinstance(img, Image.Image):
                self.__image = img
            else:
                stderr.write('图片错误:剪贴板中不包含图片\n')
                return 8
        elif self.__setting['pathtype'] == 'local':
            # 说明读本地图片
            if exists(self.__setting['path']):
                self.__image = Image.open(self.__setting['path'])
            else:
                stderr.write('图片错误:图片' + self.__setting['path'] + '不存在\n')
                return 1
        else:
            # 说明读网络图片
            try:
                f = BytesIO(b'')
                f.write(rq.get(self.__setting['path']).content)
            except:
                stderr.write('网络错误:图片获取失败\n')
                return 7
            self.__image = Image.open(f)

        self.__image = self.__image.convert('L')  # 转换为黑白
        return 0

    # public
    def CLIEntrance(self, *args, **kwargs):
        '''
用法:python bhg.py <参数>
参数
--source <图片路径名>:必选参数，指定原图路径名。

--text <文字>:必选参数，指定在原图下方添加的文字。
    添加多行文字请用逗号隔开，带空格的文字请用引号括起，如
    “ --text "带 空 格,的 文 字" ”

--fontsize <数字>:可选参数，指定每行文字的字号。
    字号之间以逗号分隔，将依次分配给每行文字。
    未分配字号的文字将自动选择字号；多出的字号将被忽略。

--lang <语种>:可选参数，指定每行文字的语种。
    语种之间以逗号分隔，将依次分配给每行文字。
    未分配语种的文字将被认为是'zh'（即汉字）；多出的语种将被忽略。
    错误选择或未选择语种的文字将有可能显示乱码。

--bg <RGB颜色值>:可选参数，指定文字背景色。
    颜色以RGB格式给出，用逗号分隔，如
    0,0,0 代表 黑色
    255,255,255 代表 白色
    若背景较暗，将会自动选择白色作为字色，反之字色则会自动选择黑色。

--savepng :可选参数，若指定该选项则会保存图片为png格式在当前目录下，
    文件名为(第一行文字).png。
        '''
        # 如果是通过命令行的Fire接口进来的，那么需要读入设定。
        if 'source' in kwargs:
            self.source(kwargs['source'][0])
        else:
            stderr.write('图片错误:缺少图片\n')
            return 6

        font_size = [0]
        if 'fontsize' in kwargs:
            try:
                font_size = [int(i) for i in kwargs['fontsize']]
            except ValueError:
                stderr.write('提示语错误:字号应为整数\n')
                return 2

        lang = ['zh']
        if 'lang' in kwargs:
            lang = kwargs['lang']

        if 'text' in kwargs:
            ret = self.text(kwargs['text'], font_size, lang)
            if ret != 0:
                return ret
        else:
            stderr.write('提示语错误:缺少提示语\n')
            return 5

        if 'bg' in kwargs:
            try:
                bgcolor = tuple([int(i) for i in kwargs['bg']])
            except ValueError:
                stderr.write('背景色错误:输入的背景色格式不正确\n')
                return 9
            ret = self.bg(bgcolor)
            if ret != 0:
                return ret

        if 'savepng' in kwargs:
            self.savepng()

        return self.make()

    def bg(self, bgcolor=(0, 0, 0, 255)):
        # 如果bgcolor不是元组
        # 或长度小于3
        # 或存在非整数元素，或存在元素>255或<0

        if (len(bgcolor) < 3)\
                or not(isinstance(bgcolor, tuple))\
                or ([i for i in bgcolor if (not isinstance(i, int))or(i > 255) or (i < 0)] != []):
            stderr.write('背景色错误:输入的背景色格式不正确\n')
            return 9

        self.__setting['bgcolor'] = bgcolor[:3]+(255,)
        return 0

    def source(self, path: str = ''):
        '''
        设定图片路径，判断图片类型。
        path(str):图片路径。
        '''
        self.__setting['path'] = path
        if re.match(r'^[\s]*http[s]?://[a-z0-9\-]*?\.[a-z0-9\-\.]*/', path, re.I) == None:
            # 说明这是一个本地文件
            self.__setting['pathtype'] = 'local'
        else:
            self.__setting['pathtype'] = 'url'
        return 0

    def text(self, s='', font_size=0, lang='zh'):
        '''
        添加位于图片下方的提示语。
        s(str or list of str):要添加的提示语。
        font_size(int or list of int):字体大小。默认的字体大小是font_min。
        lang(int or list of str):语种。对应使用的字体在font_dict里有对应。
        '''
        def ToList(v):
            v = list(v) if isinstance(
                v, tuple) else v if isinstance(v, list) else[v]
            return v

        global global_delimiter, font_min, font_max, font_dict
        s, font_size, lang = ToList(s), ToList(font_size), ToList(lang)
        if s == '':
            stderr.write('提示语错误:缺少提示语\n')
            return 5
        if isinstance(s, str):
            s = [s]

        for i in range(len(s)):
            # 提取对应字号
            this_font_size = 0
            if i < len(font_size):
                try:
                    this_font_size = int(font_size[i])
                except ValueError:
                    stderr.write('提示语错误:第' + str(i+1) + '项字号应为整数\n')
                    return 2
            # 提取对应语种
            this_lang = 'zh'
            if i < len(lang):
                this_lang = lang[i]
                if this_lang not in font_dict:
                    stderr.write('语种错误:没有名为"' + this_lang + '"的语种及对应的字体文件\n')
                    return 3
                if not exists(font_dict[this_lang]):
                    stderr.write('语种错误:名为' + this_lang +
                                 '的语种缺失字体文件' + font_dict[this_lang]+'\n')
                    return 4
            # 添加一行
            self.__setting['text'].append(s[i])
            self.__setting['fontsize'].append(this_font_size)
            self.__setting['font'].append(font_dict[this_lang])
            self.__setting['lang'].append(this_lang)
        return 0

    def savepng(self, flag=True):
        '''
        声明保存为png图片。
        '''
        self.__setting['savepng'] = flag
        return 0

    def make(self):
        '''
        生成图片。
        '''
        global font_min, font_max

        # 读图
        ret = self.__loadimg()
        if ret > 0:
            return ret

        # 计算字号。
        # 先默认全是汉字，不计行间，每个汉字的面积为 字号*字号
        # 因此字号应选择可以使一行文字排满图像宽度的字号。
        # 当计算出的字号小于font_min时，向标准错误输出 文字过多 错误，
        # 当计算出的字号大于font_max时，字号取font_max
        for i in range(len(self.__setting['text'])):
            if self.__setting['fontsize'][i] == 0:  # 如果没有手动设定字号
                self.__setting['fontsize'][i] = round(
                    self.__image.size[0] / len(self.__setting['text'][i]))
                if self.__setting['fontsize'][i] > font_max:
                    self.__setting['fontsize'][i] = font_max
                elif self.__setting['fontsize'][i] < font_min:
                    self.__setting['fontsize'][i] = font_min

        # 创建字体画布
        text_width = self.__image.size[0]  # 字体画布宽
        text_height = round(
            sum(self.__setting['fontsize']) * 1.3)  # 字体画布高，空出行间距
        text_canvas = Image.new(
            'RGBA', (text_width, text_height), self.__setting['bgcolor'])
        text_drawer = ImageDraw.Draw(text_canvas)  # 基于画布生成画笔
        text_color = (255, 255, 255, 255) if sum(self.__setting['bgcolor'][:3]) < 255 * 3 / 2 \
            else(0, 0, 0, 255)

        # 画出每种字体
        top = 0
        for i in range(len(self.__setting['text'])):
            fnt = ImageFont.truetype(
                self.__setting['font'][i], self.__setting['fontsize'][i], encoding="unic")  # 设置字体
            width, height = fnt.getsize(self.__setting['text'][i])
            left = round(text_width / 2 - width / 2)
            if left < 0:
                stderr.write("提示：第"+str(i+1)+"行文字过多,可能无法显示完整\n")
            text_drawer.text(
                (left, top), self.__setting['text'][i], font=fnt, fill=text_color[:3])
            top += round(height*1.1)  # 留出行间距

        # 创建一个新的空白画布，将原图和字体图贴上去
        self.__result = Image.new(
            'RGBA', (text_width, text_height + self.__image.size[1]), self.__setting['bgcolor'])
        self.__result.paste(self.__image, (0, 0))
        self.__result.paste(
            text_canvas, (0, self.__image.size[1], text_width, text_height + self.__image.size[1]))

        # 显示图片或保存图片
        if self.__setting['savepng']:
            self.__result.save(self.__setting['text'][0]+'.png', 'png')
        else:
            self.__result.show()
        return 0

    def clear(self):
        '清除并还原所有设置为默认值。'
        self.__setting = {
            'savepng': False,
            'text': [],
            'font': [],
            'fontsize': [],
            'lang': [],
            'path': '',  # 原图路径
            'pathtype': 'local',
            'bgcolor': (0, 0, 0, 255)
        }

        self.__image = ''  # 原图
        self.__result = ''  # 结果图
        return 0

    def list_setting(self, human_readable=False):
        "打印当前设置。"
        global font_dict
        if human_readable:
            print("图片:", end='')
            if self.__setting['path'] != '~':
                print(self.__setting['path'])
            else:
                print('剪贴板')
            print("图片类型:", end='')
            if self.__setting['pathtype'] == 'local':
                print('本地图片')
            else:
                print('网络图片')
            for i in range(len(self.__setting['text'])):
                print(
                    i+1, '."', self.__setting['text'][i], '"', sep='', end=' ')
                print('字号:', end='')
                if i >= len(self.__setting['fontsize']):
                    print('自动', end=' ')
                else:
                    print(self.__setting['fontsize'][i], end=' ')
                print('语种:', end='')
                if i >= len(self.__setting['lang']):
                    print('zh 字体文件:', font_dict['zh'])
                else:
                    print(self.__setting['lang'][i], ' 字体文件:',
                          font_dict[self.__setting['lang'][i]])
            print('背景色:', self.__setting['bgcolor'])
            print('保存图片:', end='')
            if self.__setting['savepng']:
                print('是')
            else:
                print('否')
            if self.__image != '':
                print('加载原图完成')
            else:
                print('无原图')
            if self.__result != '':
                print('生成图片完成')
            else:
                print('图片未生成(尝试make())')
        else:
            print(self.__setting)
            print(self.__image != '')
            print(self.__result != '')
        return 0


if __name__ == '__main__':
    CLI_Entrance = True
    Fire(BHG)
