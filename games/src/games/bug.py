from models import Game, Value, StringMode # type: ignore
from typing import Optional

"""Position: [if player 1's turn, add 1 to the start; if Player 0, it is implicitly 0] + 19 tiles [what player is occupying] 1 if empty, 2 if white, 3 if black
Move: [move]n - 06, 0710, 0713, 0718, 08, 071114, 071114"""

class Board:
    spaces = [(2, 0, 0), (1, 1, 0), (0, 2, 0),
              (1, 0, -1), (1, 0, 0), (0, 1, 0), (0, 1, 1),
              (0, 0, -2), (0, 0, -1), (0, 0, 0), (0, 0, 1), (0, 0, 2),
              (0, -1, -1), (0, -1, 0), (-1, 0, 0), (-1, 0, 1),
              (0, -2, 0), (-1, -1, 0), (-2, 0, 0)]

    def __init__(self, position, bugs):
        self.lst = [[[None for _ in range(5)] for _ in range(5)] for _ in range(5)]
        self.bugs = bugs
        for index in self.spaces:
            self.setitem(index, position % 10)
            position //= 10
        self.player = 1 if position else 2

    def setitem(self, index, value):
        self.lst[index[0]+2][index[1]+2][index[2]+2] = value

    def getitem(self, index):
        return self.lst[index[0]+2][index[1]+2][index[2]+2]

    def untangle(self, index):
        p = index[0] + index[1]
        q = index[1] + index[2]
        if p > 0 and q > 0:
            j = min(p, q)
        elif p < 0 and q < 0:
            j = max(p, q)
        else:
            j = 0
        return (p - j, j, q - j)

    def normalize(self, cells):
        return min(tuple(sorted(self.untangle((a - x, b - y, c - z)) for a, b, c in cells)) for x, y, z in cells)

    def neighbors(self, index):
        i = index[0]
        j = index[1]
        k = index[2]
        neighbors = []
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                for dk in [-1, 0, 1]:
                    if abs(di) + abs(dj) + abs(dk) == 1:
                        n = self.untangle((i + di, j + dj, k + dk))
                        if n in self.spaces:
                            neighbors.append(n)
        return neighbors

    def copy(self):
        new = Board(0, [])
        new.lst = [[[k for k in j] for j in i] for i in self.lst]
        new.player = self.player
        return new

    def execute_move(self, move, value):
        new = self.copy()
        new.setitem(move, value)
        return new

class Group:
    def __init__(self, index, board, bugs):
        self.indexes = [index]
        self.board = board
        self.color = board.getitem(index)
        self.size = 1
        self.shape = []
        self.bugs = bugs

    def expand(self):
        new_indexes = []
        for index in self.indexes:
            for neighbor in self.board.neighbors(index):
                if self.board.getitem(neighbor) == self.color and neighbor not in self.indexes and neighbor not in new_indexes:
                    new_indexes.append(neighbor)
        self.indexes.extend(new_indexes)
        self.size = len(self.indexes)
        if new_indexes:
            self.expand()
        self.shape = self.board.normalize(self.indexes)

    def disassemble(self, board):
        for index in self.indexes:
            board.setitem(index, 0)

    def same_shape(self, bug):
        target = bug.shape
        shape = list(self.indexes)
        for _ in range(6):
            if self.board.normalize(shape) == target or self.board.normalize([(k, j, i) for i, j, k in shape]) == target:
                return True
            shape = [self.board.canon((-k, i, j)) for i, j, k in shape]
        return False

    def try_eat(self):
        gone = []
        for index in self.indexes:
            for neighbor in self.board.neighbors(index):
                if self.board.getitem(neighbor) != self.color and self.board.getitem(neighbor) != 0:
                    for bug in self.bugs:
                        if neighbor in bug.indexes and bug.color != self.color and bug.size == self.size and bug not in gone and self.same_shape(bug):
                            gone.append(bug)
        return gone

    def try_grow(self, board):
        moves = []
        for index in self.indexes:
            for point in board.neighbors(index):
                if board.getitem(point) == 0 and point not in moves and all(board.getitem(n) != self.color or n in self.indexes for n in board.neighbors(point)):
                    moves.append(point)
        return moves

class Bug(Game):
    id = 'bug'
    variants = ["regular"]
    n_players = 2
    cyclic = False

    def __init__(self, variant_id: str):
        """
        Define instance variables here (i.e. variant information)
        """
        if variant_id not in Bug.variants:
            raise ValueError("Variant not defined")
        self._variant_id = variant_id
        pass

    def start(self) -> int:
        """
        Returns the starting position of the game.
        """
        return 10**19 # 1 and 19 zeros

    def generate_moves(self, position: int) -> list[int]:
        """
        Returns a list of positions given the input position.
        """
        # First, eat all the bugs
        # Second, return a list of available placement (1, ji)
        bugs = []
        board = Board(position, bugs)
        player = board.player
        postmoves = []
        maxsize = 0
        PostMultiverse = []
        CombinationalMoves = []
        for spot in board.spaces:
            if board.getitem(spot) != 0 and not any(spot in bug.indexes for bug in bugs):
                new = Group(spot, board, bugs)
                new.expand()
                bugs.append(new)
        for bug in bugs:
            if bug.size > maxsize:
                maxsize = bug.size

        moves = [spot for spot in board.spaces if board.getitem(spot) == 0]
        for bug in bugs:
            if bug.color == player:
                for occupied in bug.indexes:
                    for neighbor in board.neighbors(occupied):
                        if bug.size == maxsize and neighbor in moves:
                            moves.remove(neighbor)
        for move in list(moves):
            if len([bug for bug in bugs if bug.color == player and any(neighbor in bug.indexes for neighbor in board.neighbors(move))]) > 1:
                moves.remove(move)
        for move in moves:
            possibleboard = board.execute_move(move, player)
            PostMultiverse.append(possibleboard)
            postmoves.append([move])

        while PostMultiverse:
            optionboard = PostMultiverse.pop()
            premoves = postmoves.pop()
            bugs = []
            for spot in optionboard.spaces:
                if optionboard.getitem(spot) != 0 and not any(spot in bug.indexes for bug in bugs):
                    new = Group(spot, optionboard, bugs)
                    new.expand()
                    bugs.append(new)
            eaters = [bug for bug in bugs if bug.color == player and bug.try_eat()]
            changed = True
            while changed:
                changed = False
                eatboard = optionboard.copy()
                gone = []
                for bug in eaters:
                    for victim in bug.try_eat():
                        if victim not in gone:
                            gone.append(victim)
                for victim in gone:
                    victim.disassemble(eatboard)
                for bug in eaters:
                    if not bug.try_grow(eatboard):
                        eaters.remove(bug)
                        changed = True
                        break
            combinationalmoves = [[]]
            for bug in eaters:
                extended = []
                for prefix in combinationalmoves:
                    growboard = eatboard.copy() #type: ignore
                    for spot in prefix:
                        growboard.setitem(spot, player)
                    for spot in bug.try_grow(growboard):
                        extended.append(prefix + [spot])
                combinationalmoves = extended
            if not eaters or not combinationalmoves:
                CombinationalMoves.append(premoves)
            else:
                for suffix in combinationalmoves:
                    possibleboard = eatboard.copy()  # type: ignore
                    for spot in suffix:
                        possibleboard.setitem(spot, player)
                    PostMultiverse.append(possibleboard)
                    postmoves.append(premoves + suffix)

        combinationalstrings = []
        for sequence in CombinationalMoves:
            digits = str(player)
            for move in sequence:
                tile = board.spaces.index(move) + 1
                if tile < 10:
                    digits += "0" + str(tile)
                else:
                    digits += str(tile)
            combinationalstrings.append(int(digits))
        return combinationalstrings

    def unpack(self, position:int, move:int):
        """
        Unpacks moves from tiles placed to all tiles changed (hopefully)
        """
        TILE_IDS = ['11', '12', '13',
            '21', '22', '23', '24',
            '31', '32', '33', '34', '35',
            '41', '42', '43', '44',
            '51', '52', '53']
 
        s = str(move)
        player = int(s[0])
        # take every tile to be changed
        tiles = [int(s[i:i+2]) for i in range(2, len(s), 2)]
        board = Board(position, [])
        output = []

        # save all placed tiles to output
        def record(spot, value):
            tile_index = Board.spaces.index(spot) 
            output.append(str(value) + self.TILE_IDS[tile_index])

        # first tile is ordinary placement, the rest are growths
        spot = Board.spaces[tiles[0] - 1]
        board.setitem(spot, player)
        record(spot, player)

        i = 1
        while i < len(tiles):
            eaters, after = self.eat_round(board, player)
            if not eaters:
                raise ValueError(f"move {move} has growth tiles but nothing can eat")

            # find eaten tiles
            for spot in Board.spaces:
                if board.getitem(spot) != 0 and after.getitem(spot) == 0:
                    record(spot, 0)

            # each eater grows a tile   
            growth = tiles[i:i + len(eaters)]
            if len(growth) != len(eaters):
                raise ValueError(f"move {move} needs growth tiles")
            for tile in growth:
                spot = Board.spaces[tile - 1]
                after.setitem(spot, player)
                record(spot, player)
 
            board = after
            i += len(eaters)
 
        return "".join(output)

    def eat_round(self, board, player):
        """
        Same eating logic as in generate_moves, to help unpack moves into placements
        """
        bugs = []
        for spot in board.spaces:
            if board.getitem(spot) != 0 and not any(spot in b.indexes for b in bugs):
                g = Group(spot, board, bugs)
                g.expand()
                bugs.append(g)
    
        eaters = [b for b in bugs if b.color == player and b.try_eat()]
        while True:
            after = board.copy()
            for bug in eaters:
                for victim in bug.try_eat():
                    victim.disassemble(after)
            stuck = [b for b in eaters if not b.try_grow(after)]
            if not stuck:
                return eaters, after
            eaters.remove(stuck[0])

    def do_move(self, position: int, move: int) -> int:
        """
        Returns the resulting position of applying move to position.
        """
        # you get a position like 101201201201201201200 (20 digits, first digit is player turn indicator)
        # 234312 <- means change 34 to 2, which is white, change 12 to black
        # if no moves left, return 10 for white win, or 20 for black win <- goes in primitive 

        pos_str = str(position)
        player_turn = 1 if len(pos_str) == 20 else 0

        # convert move to changes
        move_str = self.unpack(position, move)

        pos_str_clean = pos_str[1:] if player_turn == 1 else pos_str.zfill(19) #remove player info because we don't need it for now

        # this converts the 3:3 gui format to the actual index position in the pos_string
        # order reversed to work with Board class
        tilenum_to_chari = {'11':18, '12':17, '13':16, 
                            '21':15, '22':14, '23':13, '24':12,
                            '31':11, '32':10, '33':9, '34':8, '35': 7, 
                            '41':6, '42':5,'43':4, '44':3,
                            '51':2,'52':1,'53':0} 

        triplets = [move_str[i : i + 3] for i in range(0, len(move_str), 3)] # changed from pos_str to move str
        changes_in_order = {tile[1] + tile[2] : tile[0] for tile in triplets}

        #iterate through the list of needed changes and apply them to the position string, allowing for multiple updates to the same tile
        for tile in changes_in_order:
            pos_str_clean = pos_str_clean[:tilenum_to_chari[tile]] + changes_in_order[tile] + pos_str_clean[tilenum_to_chari[tile] + 1:]


        #swap player turn
        updated_pos_string = str(abs(player_turn - 1)) + pos_str_clean

        return int(updated_pos_string)

    def primitive(self, position: int) -> Optional[Value]:
        """
        Returns a Value enum which defines whether the current position is a win, loss, or non-terminal.
        """
        if self.generate_moves(position=position) == []:
            return Value.Win
        return None
    
    def to_string(self, position: int, mode: StringMode) -> str:
        """
        Returns a string representation of the position based on the given mode.
        """
        return str(position)

    def from_string(self, strposition: str) -> int:
        """
        Returns the position from a string representation of the position.
        Input string is StringMode.Readable.
        """
        return int(strposition)

    def move_to_string(self, move: int, mode: StringMode) -> str:
        """
        Returns a string representation of the move based on the given mode.
        """

        return str(move)