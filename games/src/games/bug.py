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

    def _compute_neighbors(self, index):
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

    def neighbors(self, index):
        # PERF: look up the precomputed table instead of recomputing every call
        return NEIGHBORS[index]

    def copy(self):
        new = Board(0, [])
        new.lst = [[[k for k in j] for j in i] for i in self.lst]
        new.player = self.player
        return new

    def execute_move(self, move, value):
        new = self.copy()
        new.setitem(move, value)
        return new

# PERF: neighbour table built once at import time
_b = Board.__new__(Board)
NEIGHBORS = {s: _b._compute_neighbors(s) for s in Board.spaces}

# PERF: the 12 symmetries of the hex board as permutations of the 19 digit slots.
# SYM_PERMS[t][i] = slot that slot i moves to under symmetry t.
def _build_symmetries():
    idx = {s: n for n, s in enumerate(Board.spaces)}
    rot = lambda c: _b.untangle((-c[2], c[0], c[1]))
    refl = lambda c: (c[2], c[1], c[0])
    perms = []
    for mirror in (False, True):
        for r in range(6):
            perm = []
            for s in Board.spaces:
                c = refl(s) if mirror else s
                for _ in range(r):
                    c = rot(c)
                perm.append(idx[c])
            perms.append(perm)
    return perms
SYM_PERMS = _build_symmetries()
# INV_PERMS[t][j] = slot that ends up in slot j under symmetry t
INV_PERMS = [[perm.index(j) for j in range(19)] for perm in SYM_PERMS]
del _b

class Group:
    def __init__(self, index, board, bugs):
        self.indexes = [index]
        self.board = board
        self.color = board.getitem(index)
        self.size = 1
        self.shape = []
        self.bugs = bugs

    def expand(self):
        # PERF: same flood fill as before, but the shape is normalized once at the end
        # instead of at every recursion level
        while True:
            new_indexes = []
            for index in self.indexes:
                for neighbor in self.board.neighbors(index):
                    if self.board.getitem(neighbor) == self.color and neighbor not in self.indexes and neighbor not in new_indexes:
                        new_indexes.append(neighbor)
            self.indexes.extend(new_indexes)
            self.size = len(self.indexes)
            if not new_indexes:
                break
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
            shape = [self.board.untangle((-k, i, j)) for i, j, k in shape] # TEST
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
        # PERF: the solver calls primitive() (which calls generate_moves) and then
        # generate_moves() again on the same position, so reuse the last result
        cache = getattr(self, "_moves_cache", None)
        if cache is not None and cache[0] == position:
            return list(cache[1])
        # The fixed eating order below depends on tile numbers, so moves are generated on the
        # board turned to its standard orientation (the one hash_ext picks) and the tile
        # numbers are mapped back. That way rotated/mirrored boards always play identically.
        t, canon = self._canonical(position)
        inv = INV_PERMS[t]
        moves = []
        for m in self._generate_moves(canon):
            s = str(m)
            moves.append(int(s[0] + "".join(f"{inv[int(s[i:i+2]) - 1] + 1:02d}" for i in range(1, len(s), 2))))
        self._moves_cache = (position, moves)
        return list(moves)

    def hash_ext(self, position: int) -> int:
        """
        PERF: map every position to one canonical member of its symmetry class
        (6 rotations x 2 reflections) so symmetric positions are solved only once.
        The game rules are symmetric: bug shapes are compared up to rotation/reflection.
        """
        return self._canonical(position)[1]

    def _canonical(self, position: int) -> tuple[int, int]:
        """
        Returns (t, canonical position): the board turned to its standard orientation,
        and the index t of the symmetry in SYM_PERMS that does it.
        """
        s = str(position)
        if len(s) == 20:
            prefix, digits = "1", s[1:]
        else:
            prefix, digits = "", s.zfill(19)
        # slot i (Board.spaces[i]) is the i-th digit from the right
        cells = digits[::-1]
        best = None
        best_key = None
        best_t = 0
        for t, perm in enumerate(SYM_PERMS):
            out = [""] * 19
            for i, d in enumerate(cells):
                out[perm[i]] = d
            cand = "".join(out)[::-1]
            # compare player 1's tiles first, then player 2's
            key = (cand.replace("2", "0"), cand.replace("1", "0"))
            if best_key is None or key < best_key:
                best, best_key, best_t = cand, key, t
        return best_t, int(prefix + best)  # type: ignore

    def unhash_ext(self, hashed_pos: int) -> int:
        return hashed_pos

    def _generate_moves(self, position: int) -> list[int]:
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
            # Eat in a fixed order: the eater is the first of the player's bugs (in reading
            # order of its first tile) that touches an enemy bug of the same shape and can still
            # grow once that enemy bug is removed. It eats, grows by one tile (one branch per
            # possible tile), and then the check repeats until no bug can eat.
            eater, eatboard = self.find_eater(optionboard, bugs, player)
            if eater is None:
                CombinationalMoves.append(premoves)
            else:
                for spot in eater.try_grow(eatboard):
                    possibleboard = eatboard.copy()
                    possibleboard.setitem(spot, player)
                    PostMultiverse.append(possibleboard)
                    postmoves.append(premoves + [spot])

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
        # replay on the board in its standard orientation (the same one generate_moves uses)
        # and map every changed tile back to the real board
        t, position = self._canonical(position)
        perm, inv = SYM_PERMS[t], INV_PERMS[t]
        tiles = [perm[int(s[i:i+2]) - 1] + 1 for i in range(1, len(s), 2)]
        board = Board(position, [])
        output = []

        # save all placed tiles to output
        def record(spot, value):
            tile_index = inv[Board.spaces.index(spot)]
            output.append(str(value) + TILE_IDS[tile_index])

        # first tile is ordinary placement, the rest are growths
        spot = Board.spaces[tiles[0] - 1]
        board.setitem(spot, player)
        record(spot, player)

        for tile in tiles[1:]:
            eater, after = self.eat_round(board, player)
            if eater is None:
                raise ValueError(f"move {move} has growth tiles but nothing can eat")

            # find eaten tiles
            for spot in Board.spaces:
                if board.getitem(spot) != 0 and after.getitem(spot) == 0:
                    record(spot, 0)

            # the eater grows by one tile
            spot = Board.spaces[tile - 1]
            if spot not in eater.try_grow(after):
                raise ValueError(f"move {move} grows onto a tile the eater cannot grow onto")
            after.setitem(spot, player)
            record(spot, player)

            board = after

        return "".join(output)

    def eat_round(self, board, player):
        """
        Same eating logic as in generate_moves, to help unpack moves into placements.
        Returns (eater, board after the eaten bugs are removed), or (None, None).
        """
        bugs = []
        for spot in board.spaces:
            if board.getitem(spot) != 0 and not any(spot in b.indexes for b in bugs):
                g = Group(spot, board, bugs)
                g.expand()
                bugs.append(g)
        return self.find_eater(board, bugs, player)

    def find_eater(self, board, bugs, player):
        """
        Fixed eating order: returns the first of the player's bugs (bugs is in reading order
        of each bug's first tile) that has enemy bugs to eat and can still grow after they are
        removed, together with a copy of the board with those enemy bugs removed.
        Returns (None, None) if no bug can eat.
        """
        for bug in bugs:
            if bug.color != player:
                continue
            victims = bug.try_eat()
            if not victims:
                continue
            eatboard = board.copy()
            for victim in victims:
                victim.disassemble(eatboard)
            if bug.try_grow(eatboard):
                return bug, eatboard
        return None, None

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
        if self.generate_moves(position) == []:
            return Value.Win
        return None
    
    ROWS = [3, 4, 5, 4, 3]
    FILL = {'0': ' ', '1': 'W', '2': 'B'}
    # LABELS[i] is the row+column ID of Board.spaces[i] (rows 1-5 top to bottom,
    # columns counted from 1 at the left of each row), same as TILE_IDS in unpack
    LABELS = [f"{r}{c}" for r, n in enumerate(ROWS, 1) for c in range(1, n + 1)]

    def to_string(self, position: int, mode: StringMode) -> str:

        """
        Returns a string representation of the position based on the given mode.
        """
        if mode != StringMode.TUI:
            return str(position)
        digits = str(position).zfill(20)[-19:][::-1]
        P, H = 10, 4
        edge = "'-._____.-"
        canvas = [[' '] * (P * 5 + 1) for _ in range(H * 5 + 1)]
        t = 0
        for r, n in enumerate(self.ROWS):
            y, x0 = r * H, (5 - n) * P // 2
            for c in range(n):
                x, f = x0 + c * P, self.FILL[digits[t]]
                body = [f * 9, f"{f*2} {self.LABELS[t]:^3} {f*2}", f * 9]
                for k, line in enumerate(body):
                    canvas[y+1+k][x:x+P+1] = list('|' + line + '|')
                cx = x + P // 2
                for i in range(P + 1):
                    canvas[y][x+i]   = edge[(x + i - cx) % P]
                    canvas[y+H][x+i] = edge[(x + i - cx + P//2) % P]
                t += 1
        return "\n".join("".join(row).rstrip() for row in canvas)
    

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

        if mode != StringMode.TUI:
            return str(move)
        s = str(move)[1:]                     # drop the player digit
        return " ".join(self.LABELS[int(s[i:i+2]) - 1] for i in range(0, len(s), 2))