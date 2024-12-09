import time
import random
import logging
import tkinter as tk
from enum import Enum
from typing import Union

from paths import PRESS_PATH, UNPRESS_PATH, TEXT, PATH_LOG


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PATH_LOG, encoding='utf-8')
    ]
)


class python_snake:
    """
    Класс, реализующий игру "Змейка" на tkinter.
    """
    def __init__(self, window: tk.Tk,
                 canv_x: int,
                 canv_y: int,
                 canv_width: int,
                 canv_height: int):
        """
        Инициализация змейки и игрового поля.
        """
        logging.info("Initializing the Snake game")
        self.__started = 1
        self.__spped = 10
        self.__window = window
        self.__canv_x = canv_x
        self.__canv_y = canv_y
        self.canv_width = canv_width
        self.canv_height = canv_height
        self.__snake_x = self.canv_width//2
        self.__snake_y = self.canv_height//2
        self.canv = tk.Canvas(self.__window, width=self.canv_width,
                              height=self.canv_height,
                              bg=self.CONST.CANVAS_BGCOLOR.value)
        self.canv.place(x=self.__canv_x, y=self.__canv_y)
        self.create_head_food()

        logging.info("Binding controls to keyboard events")
        self.__window.bind('<d>', self.right)
        self.__window.bind('<D>', self.right)
        self.__window.bind('<Right>', self.right)
        self.__window.bind('<s>', self.down)
        self.__window.bind('<S>', self.down)
        self.__window.bind('<Down>', self.down)
        self.__window.bind('<a>', self.left)
        self.__window.bind('<A>', self.left)
        self.__window.bind('<Left>', self.left)
        self.__window.bind('<w>', self.up)
        self.__window.bind('<W>', self.up)
        self.__window.bind('<Up>', self.up)

        self.__window.bind('<e>', self.move)
        self.__window.bind('<q>', self.quit)
        self.__window.bind('<Destroy>', self.quit)
        self.__window.bind('<plus>', self.speed_key)
        self.__window.bind('<minus>', self.speed_key)
        self.__window.bind('<KP_Add>', self.speed_key)
        self.__window.bind('<KP_Subtract>', self.speed_key)

    class CONST(Enum):
        RIGHT = 1
        DOWN = 2
        LEFT = 3
        UP = 4
        SNAKE_HCOLOR = 'red'
        SNAKE_BCOLOR = 'green'
        CANVAS_BGCOLOR = '#bfcff1'
        SNAKE_THICKNESS = 11
        FOOD_THICKNESS = 15
        FOOD_COLOR = '#aced95'
        EXPLOSIVE = 15
        EXPLOSIVE_BORD = 10
        EXPLOSIVE_BCOLOR = '#ff9999'
        EXPLOSIVE_CCOLOR = '#881a1a'

    def right(self, event: tk.Event) -> None:
        """Обработчик клавиши 'вправо'."""
        logging.info("Changing direction to RIGHT")
        self.__vector = self.CONST.RIGHT.value

    def down(self, event: tk.Event) -> None:
        """Обработчик клавиши 'вниз'."""
        logging.info("Changing direction to DOWN")
        self.__vector = self.CONST.DOWN.value

    def left(self, event: tk.Event) -> None:
        """Обработчик клавиши 'влево'."""
        logging.info("Changing direction to LEFT")
        self.__vector = self.CONST.LEFT.value

    def up(self, event: tk.Event) -> None:
        """Обработчик клавиши 'вверх'."""
        logging.info("Changing direction to UP")
        self.__vector = self.CONST.UP.value

    def speed_key(self, event: tk.Event) -> None:
        """
        Обработчик клавиш изменения скорости. 
        Увеличивает или уменьшает скорость змейки.
        """
        if event.keysym == 'KP_Add' or event.keysym == 'plus':
            logging.info("Increasing speed")
            self.speed('+')
        elif event.keysym == 'KP_Subtract' or event.keysym == 'minus':
            logging.info("Decreasing speed")
            self.speed('-')

    def create_head_food(self) -> None:
        """
        Создает голову змейки, еду и начальное тело.
        """
        rand_vect = random.randint(1, 4)
        logging.info("Creating the snake's head and initial body")
        if rand_vect == 1:
            self.__vector = self.CONST.RIGHT.value
        elif rand_vect == 2:
            self.__vector = self.CONST.DOWN.value
        elif rand_vect == 3:
            self.__vector = self.CONST.LEFT.value
        else:
            self.__vector = self.CONST.UP.value
        self.head = self.element_square(self, self.__snake_x,
                                        self.__snake_y,
                                        self.CONST.SNAKE_THICKNESS.value,
                                        self.CONST.SNAKE_HCOLOR.value)
        self.food.add(self)
        self.body = []
        self.body.append({'id': self.head.draw(),
                          'x': self.__snake_x,
                          'y': self.__snake_y})
        self.step('add')
        self.step('add')
        self.step('add')
        self.step('add')
        logging.info("Snake and food created successfully")

    def speed(self, way: str) -> None:
        """
        Меняет скорость змейки.
        """
        if way == '+' and self.__spped > 1:
            self.__spped -= 1
            logging.info(f"Speed increased. Current speed: {self.__spped}")
        elif way == '-' and self.__spped < 20:
            self.__spped += 1
            logging.info(f"Speed decreased. Current speed: {self.__spped}")

    def reload(self) -> None:
        """
        Перезапускает игру, сбрасывая все параметры и начальные условия.
        """
        logging.info("Reloading the game")
        self.quit = 'n'
        self.__started = 1
        self.__spped = 10
        self.canv.delete('all')
        del self.body
        self.body = []
        self.create_head_food()
        self.start()

    def quit(self, event: tk.Event) -> None:
        """Останавливает игру (пауза)."""
        logging.info("Game paused")
        self.quit = 'y'

    def move(self, event: tk.Event) -> None:
        """Запускает движение змейки, если игра не на паузе."""
        if self.quit != 'n':
            logging.info("Starting snake movement")
            self.start()

    def start(self) -> None:
        """
        Основной игровой цикл. Управляет движением змейки,
        проверкой столкновений и поеданием пищи.
        """
        logging.info("Game started")
        if self.__started == 1:
            self.quit = 'n'
            i = 0
            add = 'del'
            while i == 0:
                self.step(add)
                if self.food.eat(self) == 1:
                    logging.info("Food eaten")
                    add = 'add'
                    self.speed('+')
                elif add == 'add':
                    add = 'del'
                if self.bump_wall() == 'the end':
                    logging.warning("Snake collided with wall")
                    break
                if self.bump_body() == 'the end':
                    logging.warning("Snake collided with itself")
                    break
                for x in range(1, (self.__spped + 1)):
                    time.sleep(0.05)
                    self.__window.update()
                    if self.quit == 'y':
                        logging.info("Game paused during gameplay")
                        i = 1
                        break

    def bump_wall(self) -> Union[str, int]:
        """
        Проверяет, столкнулась ли змейка со стеной.
        """
        __head_x = self.body[-1]['x']
        __head_y = self.body[-1]['y']
        if ((__head_x < ((self.CONST.SNAKE_THICKNESS.value//2)+1))
            or (__head_y < ((self.CONST.SNAKE_THICKNESS.value//2)+1))
            or (__head_x > (self.canv_width
                            - (self.CONST.SNAKE_THICKNESS.value//2)+1))
            or (__head_y > (self.canv_height
                            - (self.CONST.SNAKE_THICKNESS.value//2)+1))):
            self.explosive()
            logging.warning("Collision with wall detected")
            return 'the end'
        else:
            return 0

    def bump_body(self) -> Union[str, int]:
        """
        Проверяет, столкнулась ли змейка с собственным телом.
        """
        __head_x = self.body[-1]['x']
        __head_y = self.body[-1]['y']
        bump = 0
        for i in range(0, (len(self.body)-1)):
            if ((__head_x == self.body[i]['x'])
                    and (__head_y == self.body[i]['y'])):
                self.explosive()
                logging.warning("Collision with the snake's body detected")
                bump = 'the end'
        return bump

    def explosive(self) -> None:
        """
        Отображает взрыв на холсте в случае столкновения змейки.
        """
        logging.info("Displaying explosion animation")
        self.__started = 0
        self.canv.create_oval((self.body[-1]['x']
                               - self.CONST.EXPLOSIVE.value),
                              (self.body[-1]['y']
                               - self.CONST.EXPLOSIVE.value),
                              (self.body[-1]['x']
                               + self.CONST.EXPLOSIVE.value),
                              (self.body[-1]['y']
                               + self.CONST.EXPLOSIVE.value),
                              fill=self.CONST.EXPLOSIVE_BCOLOR.value,
                              outline=self.CONST.EXPLOSIVE_CCOLOR.value,
                              width=self.CONST.EXPLOSIVE_BORD.value)

    def step(self, add: str) -> None:
        """
        Двигает змейку в текущем направлении.
        """
        if self.__vector == self.CONST.RIGHT.value:
            deltax = self.CONST.SNAKE_THICKNESS.value
            deltay = 0
        elif self.__vector == self.CONST.DOWN.value:
            deltax = 0
            deltay = self.CONST.SNAKE_THICKNESS.value
        elif self.__vector == self.CONST.LEFT.value:
            deltax = -self.CONST.SNAKE_THICKNESS.value
            deltay = 0
        elif self.__vector == self.CONST.UP.value:
            deltax = 0
            deltay = -self.CONST.SNAKE_THICKNESS.value
        self.head.x += deltax
        self.head.y += deltay
        self.head = self.element_square(self, self.head.x, self.head.y,
                                        self.CONST.SNAKE_THICKNESS.value,
                                        self.CONST.SNAKE_HCOLOR.value)
        self.body.append({'id': self.head.draw(), 'x': self.head.x,
                          'y': self.head.y})
        self.canv.itemconfig(self.body[-2]['id'],
                             fill=self.CONST.SNAKE_BCOLOR.value)
        if add != 'add':
            self.canv.delete(self.body[0]['id'])
            self.body.pop(0)

    class food:
        def add(self) -> None:
            """
            Создает новую еду в случайной позиции на холсте.
            """
            logging.info("Creating new food at a random position")
            self.food.x = random.randint(self.CONST.FOOD_THICKNESS.value
                                         // 2, self.canv_width
                                         - self.CONST.FOOD_THICKNESS.value//2)
            self.food.y = random.randint(self.CONST.FOOD_THICKNESS.value
                                         // 2, self.canv_height
                                         - self.CONST.FOOD_THICKNESS.value//2)
            self.food.body = self.element_square(
                                                self,
                                                self.food.x,
                                                self.food.y,
                                                self.CONST.FOOD_THICKNESS.value,
                                                self.CONST.FOOD_COLOR.value)
            self.food.id = self.food.body.draw()
            logging.info(f"Food created at ({self.food.x}, {self.food.y})")

        def eat(self) -> None:
            """
            Проверяет, съела ли змейка еду.
            """
            head_x = self.body[-1]['x']
            head_y = self.body[-1]['y']
            eat = 0
            if (
                (head_x + self.CONST.SNAKE_THICKNESS.value // 2 >
                self.food.x - self.CONST.FOOD_THICKNESS.value // 2)
                and (head_x - self.CONST.SNAKE_THICKNESS.value // 2 <
                    self.food.x + self.CONST.FOOD_THICKNESS.value // 2)
                and (head_y + self.CONST.SNAKE_THICKNESS.value // 2 >
                    self.food.y - self.CONST.FOOD_THICKNESS.value // 2)
                and (head_y - self.CONST.SNAKE_THICKNESS.value // 2 <
                    self.food.y + self.CONST.FOOD_THICKNESS.value // 2)
            ):
                logging.info("Food eaten by snake!")
                self.canv.delete(self.food.id)
                self.food.add(self)
                eat = 1
            return eat

    class element_square:
        def __init__(self, self_glob, x, y, d, color) -> None:
            """
            Инициализация квадратного элемента.
            """
            self.self_glob = self_glob
            self.x = x
            self.y = y
            self.d = d
            self.color = color
            if (self.d % 2) == 0:
                self.d += 1
            logging.debug(f"Element created at ({self.x}, {self.y}) with size {self.d} and color {self.color}")

        def draw(self) -> None:
            """
            Рисует квадратный элемент на холсте.
            """
            x = self.x-(self.d//2)
            y = self.y-(self.d//2)
            logging.info(f"Drawing element at ({x}, {y}) with size {self.d}")
            return self.self_glob.canv.create_rectangle(x, y, x+self.d,
                                                        y+self.d,
                                                        fill=self.color,
                                                        width=2)


def main() -> None:
    """
    Основная функция, запускающая приложение "Змейка".
    """
    logging.info("Starting the Snake game application")
    image1_data = PRESS_PATH
    image2_data = UNPRESS_PATH

    def button_press(a) -> None:
        """Меняет изображение кнопки при нажатии."""
        logging.info("Reload button pressed")
        reload_button['image'] = reload_button_img2
        snake.reload()

    def button_unpress(a) -> None:
        """Возвращает изображение кнопки при отпускании."""
        logging.info("Reload button released")
        reload_button['image'] = reload_button_img1

    logging.info("Initializing the main tkinter window")
    root = tk.Tk()
    root.title('Программа Змейка на питоне в графике')
    root.geometry('800x600+150+150')

    logging.info("Setting up the main window frame and text")
    frame = tk.Frame(root, width=740, height=90, bg='#f2ffe0')
    frame.place(x=30, y=5)
    text = tk.Label(root, text=TEXT, bg='#f2ffe0', width=79)
    text.place(x=30, y=10)
    reload_button_img1 = tk.PhotoImage(file=image1_data)
    reload_button = tk.Label(image=reload_button_img1, bg='#f2ffe0')
    reload_button.place(x=675, y=13)
    reload_button_img2 = tk.PhotoImage(file=image2_data)
    reload_button.bind('<Button-1>', button_press)
    reload_button.bind('<ButtonRelease-1>', button_unpress)

    logging.info("Creating Snake game instance")
    snake = python_snake(root, 30, 100, 740, 470)
    logging.info("Starting the Snake game")
    snake.start()

    logging.info("Running the main tkinter event loop")
    root.mainloop()


if __name__ == '__main__':
    main()
