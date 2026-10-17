from flask import Flask, render_template, jsonify, request
import random

app = Flask(__name__)

BOARD_SIZE = 15
board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
history = []  # 记录步骤 [(x, y, player), ...]
ai_difficulty = 'medium'  # 'easy', 'medium', 'hard'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def make_move():
    global board, history
    data = request.json
    x, y = data['x'], data['y']
    mode = data.get('mode', 'pve')
    current_player = data.get('current_player', 1)

    if board[y][x] != 0:
        return jsonify({"success": False, "message": "该位置已有棋子！"})

    # 1. 当前玩家落子
    board[y][x] = current_player
    history.append((x, y, current_player))

    if check_win(x, y, current_player):
        return jsonify({"success": True, "board": board, "winner": current_player, "last_move": [x, y]})

    # 2. 如果是人机模式 (PvE)，AI 自动应答
    ai_move_coord = None
    if mode == 'pve' and current_player == 1:
        ai_move_coord = get_ai_move()
        if ai_move_coord:
            ax, ay = ai_move_coord
            board[ay][ax] = 2
            history.append((ax, ay, 2))
            if check_win(ax, ay, 2):
                return jsonify({"success": True, "board": board, "winner": 2, "last_move": [ax, ay]})

    last_pos = [history[-1][0], history[-1][1]] if history else None
    return jsonify({
        "success": True, 
        "board": board, 
        "winner": 0, 
        "last_move": last_pos,
        "ai_move": ai_move_coord
    })

@app.route('/undo', methods=['POST'])
def undo():
    global board, history
    data = request.json
    mode = data.get('mode', 'pve')

    if not history:
        return jsonify({"success": False, "message": "无棋可悔"})

    # PvE撤销两步，PvP撤销一步
    steps = 2 if (mode == 'pve' and len(history) >= 2) else 1
    for _ in range(steps):
        if history:
            hx, hy, _ = history.pop()
            board[hy][hx] = 0

    last_pos = [history[-1][0], history[-1][1]] if history else None
    return jsonify({"success": True, "board": board, "last_move": last_pos})

@app.route('/hint', methods=['POST'])
def hint():
    best = get_best_evaluated_move()
    return jsonify({"success": True, "hint": best})

@app.route('/reset', methods=['POST'])
def reset():
    global board, history, ai_difficulty
    board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    history.clear()
    data = request.json or {}
    ai_difficulty = data.get('difficulty', 'medium')
    return jsonify({"success": True, "board": board})

# ================= 胜负与 AI 逻辑算法 =================

def check_win(x, y, player):
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for dx, dy in directions:
        count = 1
        nx, ny = x + dx, y + dy
        while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == player:
            count += 1
            nx += dx
            ny += dy
        nx, ny = x - dx, y - dy
        while 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] == player:
            count += 1
            nx -= dx
            ny -= dy
        if count >= 5:
            return True
    return False

def get_ai_move():
    if ai_difficulty == 'easy':
        return get_random_neighbor_move()
    return get_best_evaluated_move()

def has_neighbor(x, y):
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and board[ny][nx] != 0:
                return True
    return False

def get_random_neighbor_move():
    candidates = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == 0 and has_neighbor(x, y):
                candidates.append((x, y))
    return random.choice(candidates) if candidates else (7, 7)

def get_best_evaluated_move():
    best_score = -1
    best_moves = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] == 0:
                if not has_neighbor(x, y) and len(history) > 0:
                    continue
                attack = evaluate_point(x, y, player=2)
                defend = evaluate_point(x, y, player=1)
                weight = 1.2 if ai_difficulty == 'hard' else 1.0
                total = attack * weight + defend

                if total > best_score:
                    best_score = total
                    best_moves = [(x, y)]
                elif total == best_score:
                    best_moves.append((x, y))
    return random.choice(best_moves) if best_moves else (7, 7)

def evaluate_point(x, y, player):
    score = 0
    directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
    for dx, dy in directions:
        line = get_line_pattern(x, y, dx, dy, player)
        score += pattern_to_score(line)
    return score

def get_line_pattern(x, y, dx, dy, player):
    pattern = []
    for i in range(-4, 5):
        if i == 0:
            pattern.append('1')
            continue
        nx, ny = x + i * dx, y + i * dy
        if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
            p = board[ny][nx]
            if p == player:
                pattern.append('1')
            elif p == 0:
                pattern.append('0')
            else:
                pattern.append('2')
        else:
            pattern.append('2')
    return "".join(pattern)

def pattern_to_score(pattern):
    if "11111" in pattern: return 100000
    if "011110" in pattern: return 10000
    if "011112" in pattern or "211110" in pattern or "10111" in pattern or "11101" in pattern: return 2000
    if "01110" in pattern or "010110" in pattern or "011010" in pattern: return 1000
    if "001112" in pattern or "211100" in pattern: return 200
    if "001100" in pattern or "01010" in pattern: return 100
    return 10

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)