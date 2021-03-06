#
# LODE RUNNER
# 
# Jacob Kingery and Allison Patterson
#
# We added better-than-nothing baddie AI, non-teleporting falling,
# sound effects, and background music.
#
# Sounds used:
# http://freesound.org/people/WIM/sounds/19914/ (cut from)
# http://freesound.org/people/GabrielAraujo/sounds/242501/
# http://freesound.org/people/GabrielAraujo/sounds/242503/
# http://freesound.org/people/fotoshop/sounds/47356/
# http://freesound.org/people/Zott820/sounds/209578/
#
# Background music:
# http://incompetech.com/music/royalty-free/index.html?isrc=USUAN1400024


from graphics import *
import pygame.mixer  # For sound effects only
import random
import time

LEVEL_WIDTH = 35
LEVEL_HEIGHT = 20    

CELL_SIZE = 24
WINDOW_WIDTH = CELL_SIZE*LEVEL_WIDTH
WINDOW_HEIGHT = CELL_SIZE*LEVEL_HEIGHT

GR_OBS = {'hidden':[]}

BADDIE_DELAY = 25
HOLE_DELAY = 350

# Sound effect setup
pygame.mixer.init(44100,-16,2,4096)
GOLD_SND = pygame.mixer.Sound('sounds/gold_snd.wav')
FALL_SND = pygame.mixer.Sound('sounds/fall_snd.wav')
DIG_SND = pygame.mixer.Sound('sounds/dig_snd.wav')
WIN_SND = pygame.mixer.Sound('sounds/win_snd.wav')
LOSE_SND = pygame.mixer.Sound('sounds/lose_snd.wav')


def screen_pos (x,y):
    return (x*CELL_SIZE+10,y*CELL_SIZE+10)

def screen_pos_index (index):
    x = index % LEVEL_WIDTH
    y = (index - x) / LEVEL_WIDTH
    return screen_pos(x,y)

def index (x,y):
    return x + (y*LEVEL_WIDTH)

class Queue (object):
    def __init__ (self):
        self._queue = []

    def enqueue (self,delay,obj):
        self._queue.append((delay, obj))
        self._queue.sort()

    def dequeue_if_ready (self):
        while self._queue[0][0] == 0:
            evt = self._queue.pop(0)
            evt[1].event(self)
        self._queue = [(x-1,obj) for x,obj in self._queue]


class Hole (object):
    def __init__ (self,x,y,window,level):
        self._x = x
        self._y = y
        self._window = window
        self._level = level

    def event (self,q):        
        sx,sy = screen_pos(self._x,self._y)
        self._level[index(self._x,self._y)] = 1
        GR_OBS[(sx,sy)].draw(self._window)


class Character (object):
    def __init__ (self,pic,x,y,window,level,q):
        (sx,sy) = screen_pos(x,y)
        self._img = Image(Point(sx+CELL_SIZE/2,sy+CELL_SIZE/2+2),pic)
        self._window = window
        self._img.draw(window)
        self._x = x
        self._y = y
        self._level = level
        self._q = q
        self._fell = 0

    def erase (self):
        self._img.undraw()

    def same_loc (self,x,y):
        return (self._x == x and self._y == y)

    def get_surroundings (self):
        up = self._level[index(self._x, self._y-1)]
        down = self._level[index(self._x, self._y+1)]
        left = self._level[index(self._x-1, self._y)]
        right = self._level[index(self._x+1, self._y)]

        return {'u':up, 'd':down, 'l':left, 'r':right}

    def move (self,dx,dy):
        self._fell = 0
        tx = self._x + dx
        ty = self._y + dy
        if tx >= 0 and ty >= 0 and tx < LEVEL_WIDTH and ty < LEVEL_HEIGHT:
            old_pos = self._level[index(self._x,self._y)]
            new_pos = self._level[index(tx,ty)]
            if dx:
                if new_pos == 1:
                    return
            if dy == 1:
                if new_pos == 1:
                    return
            if dy == -1:
                if old_pos not in (2,9) or new_pos == 1:
                    return

            self._x = tx
            self._y = ty
            self._img.move(dx*CELL_SIZE,dy*CELL_SIZE)
            self.should_fall()
            if self._fell:
                FALL_SND.play()


    def should_fall (self):
        if self._y < LEVEL_HEIGHT - 1:
            curr = self._level[index(self._x,self._y)]
            below = self._level[index(self._x,self._y+1)]
            if curr == 0 and below in (0,3,4):
                time.sleep(.08)
                self.fall()


    def fall (self):
        if self._level[index(self._x,self._y)] != 3 and self._level[index(self._x,self._y+1)] != 1:
            self._fell = 1
            self._img.move(0,1*CELL_SIZE)
            self._y +=1
            time.sleep(.05)
            self.should_fall()

class Player (Character):
    def __init__ (self,x,y,window,level,q):
        Character.__init__(self,'sprites/t_android.gif',x,y,window,level,q)

    def at_exit (self):
        return (self._y == 0)

    def pickup_gold (self):
        tx = self._x
        ty = self._y
        if self._level[index(tx,ty)] == 4:
            GOLD_SND.play()
            self._level[index(tx,ty)] = 0
            sx, sy = screen_pos(tx,ty)
            GR_OBS[(sx,sy)].undraw()

        if 4 not in self._level:
            for hl in GR_OBS['hidden']:
                hl.undraw()
        
    def make_hole (self, tx, ty):
        self._level[index(tx,ty)] = 0
        sx, sy = screen_pos(tx,ty)
        GR_OBS[(sx,sy)].undraw()

        hole = Hole(tx,ty,self._window,self._level)
        self._q.enqueue(HOLE_DELAY,hole)

    def dig (self,dx):
        if self._y != LEVEL_HEIGHT - 1:
            tx = self._x + dx
            ty = self._y + 1
            if self._level[index(tx,ty)] == 1 and self._level[index(tx,self._y)] == 0:
                DIG_SND.play()
                self.make_hole(tx,ty)

    def is_crushed (self):
        if self._level[index(self._x,self._y)] == 1:
            lost(self._window)

class Baddie (Character):
    def __init__ (self,x,y,window,level,player,q):
        Character.__init__(self,'sprites/t_red.gif',x,y,window,level,q)
        self._player = player

    def dist_to_player(self):
        dx = self._player._x - self._x
        dy = self._player._y - self._y
        return dx,dy

    def event (self,q):
        if not self.is_crushed():
            distx,disty = self.dist_to_player()
            dx,dy = random.choice([(0,sign(disty)),(sign(distx),0)])
            self.move(dx,dy)
            q.enqueue(BADDIE_DELAY, self)  
        else:
            self.erase()

    def is_crushed (self):
        if self._level[index(self._x,self._y)] == 1:
            return True


def sign (x):
    return (x > 0) - (x < 0)

def lost (window):
    LOSE_SND.play()
    t = Text(Point(WINDOW_WIDTH/2+10,WINDOW_HEIGHT/2+10),'YOU LOST!')
    t.setSize(36)
    t.setTextColor('red')
    t.draw(window)
    window.getKey()
    time.sleep(.5)
    exit(0)

def won (window):
    WIN_SND.play()
    t = Text(Point(WINDOW_WIDTH/2+10,WINDOW_HEIGHT/2+10),'YOU WON!')
    t.setSize(36)
    t.setTextColor('red')
    t.draw(window)
    window.getKey()
    exit(0)



# 0 empty
# 1 brick
# 2 ladder
# 3 rope
# 4 gold
# 9 hidden ladder

def create_level (num):
    screen = [1,1,1,1,1,1,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0,2,1,1,1,1,1,1,1,1,1,1,1,1,9,
              1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,
              1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0,0,0,4,0,0,0,0,9,
              1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,1,
              0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,1,2,1,0,0,0,1,2,0,1,
              0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,1,1,1,1,
              3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,2,0,0,0,0,0,0,0,0,2,0,0,0,0,3,3,3,3,
              2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,
              2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,
              2,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,0,0,0,0,0,0,2,1,1,1,1,1,1,1,2,
              2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,2,
              2,0,0,0,0,0,3,3,0,0,0,0,0,0,3,3,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,2,
              2,0,1,1,1,1,0,0,1,1,1,1,1,1,0,0,1,2,1,0,0,0,0,3,3,3,2,0,0,1,1,1,1,1,2,
              2,0,1,0,0,1,0,0,1,0,0,0,0,1,0,0,1,2,1,1,1,1,1,1,0,0,2,0,0,1,0,0,0,1,2,
              2,0,1,4,4,1,0,0,1,0,4,4,4,1,0,0,1,2,0,4,4,4,0,1,0,0,2,0,0,1,4,4,4,1,2,
              2,0,1,1,1,1,0,0,1,2,1,1,1,1,0,0,1,1,1,1,1,1,1,1,0,0,2,0,0,1,1,1,1,1,2,
              2,0,3,3,3,3,3,3,3,2,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,2,3,3,3,3,3,3,3,2,
              1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,1,
              1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,4,0,0,0,0,0,2,0,0,0,0,0,0,0,1,
              1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

    # screen = [1,1,1,1,1,1,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0,2,1,1,1,1,1,1,1,1,1,1,1,1,9,
    #           1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,
    #           1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,9,
    #           1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,1,
    #           0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,1,2,1,0,0,0,1,2,0,1,
    #           0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,2,0,0,0,0,1,1,1,1,
    #           3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,2,0,0,0,0,0,0,0,0,2,0,0,0,0,3,3,3,3,
    #           2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,1,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,
    #           2,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,
    #           2,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,0,0,0,0,0,0,2,1,1,1,1,1,1,1,2,
    #           2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,2,
    #           2,0,0,0,0,0,3,3,0,0,0,0,0,0,3,3,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,2,
    #           2,0,1,1,1,1,0,0,1,1,1,1,1,1,0,0,1,2,1,0,0,0,0,3,3,3,2,0,0,1,1,1,1,1,2,
    #           2,0,1,0,0,1,0,0,1,0,0,0,0,1,0,0,1,2,1,1,1,1,1,1,0,0,2,0,0,1,0,0,0,1,2,
    #           2,0,1,1,1,1,0,0,1,0,4,4,4,1,0,0,1,2,0,1,1,1,0,1,0,0,2,0,0,1,1,1,1,1,2,
    #           2,0,1,1,1,1,0,0,1,2,1,1,1,1,0,0,1,1,1,1,1,1,1,1,0,0,2,0,0,1,1,1,1,1,2,
    #           2,0,3,3,3,3,3,3,3,2,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,2,3,3,3,3,3,3,3,2,
    #           1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,1,
    #           1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,4,0,0,0,0,0,2,0,0,0,0,0,0,0,1,
    #           1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]

    return screen

def create_screen (level,window):

    tiles = {
        1: 'sprites/brick.gif',
        2: 'sprites/ladder.gif',
        3: 'sprites/rope.gif',
        4: 'sprites/gold.gif',
        9: 'sprites/ladder.gif'
    }

    
    def image (sx,sy,what):
        return Image(Point(sx+CELL_SIZE/2,sy+CELL_SIZE/2),what)

    for (index,cell) in enumerate(level):
        if cell != 0:
            (sx,sy) = screen_pos_index(index)
            elt = image(sx, sy, tiles[cell])
            elt.draw(window)
            GR_OBS[(sx,sy)] = elt
        if cell == 9:
            elt = Rectangle(Point(sx,sy), Point(sx+CELL_SIZE,sy+CELL_SIZE))
            elt.setFill('white')
            elt.setOutline('white')
            elt.draw(window)
            GR_OBS['hidden'].append(elt)


MOVE = {
    'Left': (-1,0),
    'Right': (1,0),
    'Up' : (0,-1),
    'Down' : (0,1)
}
DIG = {
    'z': -1,
    'x': 1
}

def main ():
    
    # Graphics setup
    window = GraphWin("Maze", WINDOW_WIDTH+20, WINDOW_HEIGHT+20)

    rect = Rectangle(Point(5,5),Point(WINDOW_WIDTH+15,WINDOW_HEIGHT+15))
    rect.setFill('sienna')
    rect.setOutline('sienna')
    rect.draw(window)
    rect = Rectangle(Point(10,10),Point(WINDOW_WIDTH+10,WINDOW_HEIGHT+10))
    rect.setFill('white')
    rect.setOutline('white')
    rect.draw(window)

    level = create_level(1)

    screen = create_screen(level,window)

    q = Queue()

    p = Player(17,18,window,level,q)

    # Baddie creation and event enqueuement
    BADDIES = [
               Baddie(32,11,window,level,p,q),
               Baddie(33,4,window,level,p,q),
               Baddie(15,7,window,level,p,q),
            ]
    for baddie in BADDIES:
        q.enqueue(BADDIE_DELAY, baddie)

    # Background music
    pygame.mixer.music.load('sounds/background.mp3')
    pygame.mixer.music.play(-1)

    while not p.at_exit():
        key = window.checkKey()
        p.is_crushed()
        if key == 'q':
            window.close()
            exit(0)
        if key in MOVE:
            (dx,dy) = MOVE[key]
            p.move(dx,dy)
            p.pickup_gold()
        if key in DIG:
            dx = DIG[key]
            p.dig(dx)

        # Check if player and baddie are on same tile or if 
        # baddie should fall (from hole being dug underneath)
        for baddie in BADDIES:
            if p.same_loc(baddie._x,baddie._y):
                lost(window)
            baddie.should_fall()

        # Process event queue
        q.dequeue_if_ready()

        time.sleep(.01)

    won(window)

if __name__ == '__main__':
    main()
