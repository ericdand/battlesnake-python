from AStar import *
import bottle
import copy
import math
import os

SNEK_BUFFER = 3
SNAKE = 1
WALL = 2
FOOD = 3
SAFTEY = 5

def direction(from_cell, to_cell):
    dx = to_cell[0] - from_cell[0]
    dy = to_cell[1] - from_cell[1]

    if dx == 1:
        return 'right'
    elif dx == -1:
        return 'left'
    elif dy == -1:
        return 'up'
    elif dy == 1:
        return 'down'

def distance(p, q):
    dx = abs(p[0] - q[0])
    dy = abs(p[1] - q[1])
    return dx + dy;

def closest(items, start):
    closest_item = None
    closest_distance = 10000

    # TODO: use builtin min for speed up
    for item in items:
        item_distance = distance(start, item)
        if item_distance < closest_distance:
            closest_item = item
            closest_distance = item_distance

    return closest_item

def init(data):
    grid = [[0 for col in xrange(data['height'])] for row in xrange(data['width'])]
    for snek in data['snakes']:
        if snek['id']== data['you']:
            mysnake = snek
        for coord in snek['coords']:
            grid[coord[0]][coord[1]] = SNAKE

    for f in data['food']:
        grid[f[0]][f[1]] = FOOD

    return mysnake, grid

@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')


@bottle.get('/')
def index():
    head_url = '%s://%s/static/head.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    return {
        'color': '#00ff00',
        'head': head_url
    }

# Input format:
# {
#   "width": int,
#   "height": int,
#   "game_id": uuid
# }
@bottle.post('/start')
def start():
    data = bottle.request.json

    # Response format:
    # {
    #     "color": "#FF0000",
    #     "secondary_color": "#00FF00",
    #     "head_url": "http://placecage.com/c/100/100",
    #     "name": "Cage Snake",
    #     "taunt": "OH GOD NOT THE BEES"
    #     "head_type": "pixel",
    #     "tail_type": "pixel"
    # }
    return {
        'name': 'sneeky-snek',
        'taunt': "I'm a sneeky snek!",
        'color': '#FF55FF',
        'secondary_color': '#55AA55',
        'head_url': 'https://github.com/ericdand/battlesnake-python/raw/master/static/head.png',
        'head_type': 'tongue',
        'tail_type': 'block-bum'
    }

# DATA OBJECT
# {
#     "game": "hairy-cheese",
#     "turn": 4,
#     "height": 20,
#     "width": 30,
#     "snakes": [
#         <Snake Object>, <Snake Object>, ...
#     ],
#     "food": [
#         [1, 2], [9, 3], ...
#     ]
# }

# SNAKE
# {
#   "taunt": "git gud",
#   "name": "my-snake",
#   "id": "5b079dcd-0494-4afd-a08e-72c9a7c2d983",
#   "health_points": 93,
#   "coords": [
#     [0, 0],
#     [0, 0],
#     [0, 0]
#   ]
# }

@bottle.post('/move')
def move():
    data = bottle.request.json
    snek, grid = init(data)

    # Dodge other snakes.
    for enemy in data['snakes']:
        if (enemy['id'] == data['you']):
            continue
        if distance(snek['coords'][0], enemy['coords'][0]) > SNEK_BUFFER:
            continue
        if (len(enemy['coords']) > len(snek['coords'])-1):
            #dodge
            if enemy['coords'][0][1] < data['height']-1:
                grid[enemy['coords'][0][0]][enemy['coords'][0][1]+1] = SAFTEY
            if enemy['coords'][0][1] > 0:
                grid[enemy['coords'][0][0]][enemy['coords'][0][1]-1] = SAFTEY

            if enemy['coords'][0][0] < data['width']-1:
                grid[enemy['coords'][0][0]+1][enemy['coords'][0][1]] = SAFTEY
            if enemy['coords'][0][0] > 0:
                grid[enemy['coords'][0][0]-1][enemy['coords'][0][1]] = SAFTEY

    
    snek_head = snek['coords'][0]
    snek_coords = snek['coords']
    path = None
    middle = [data['width'] / 2, data['height'] / 2]
    foods = sorted(data['food'], key = lambda p: distance(p,middle))

    # If there's only one food and we're the healthiest snek,
    # then we can try to starve out the other sneks.
    if len(foods) == 1:
        least_hungry_snek = True
        for enemy in data['snakes']:
            if enemy['id'] == data['you']:
                continue
            if enemy['health_points'] > snek['health_points']:
                least_hungry_snek = False
        if least_hungry_snek:
            # Encircle the food in an attempt to starve other snakes.
            path = a_star(snek_head, foods[0], grid, snek_coords)
            # if not path:
            # NOTE: Eric is working on this right now!

    if not path:
        for food in foods:
            #print food
            tentative_path = a_star(snek_head, food, grid, snek_coords)
            if not tentative_path:
                print "no path to food"
                continue

            path_length = len(tentative_path)
            snek_length = len(snek_coords) + 1

            can_reach_food = True
            for enemy in data['snakes']:
                if enemy['id'] == data['you']:
                    continue
                pathing_epsilon = max(data['width'], data['height'])/4
                # When racing another snake to food, we will go for the food if no
                # other snek is pathing_epsilon spaces closer than us.
                if path_length > distance(enemy['coords'][0], food) + pathing_epsilon:
                    can_reach_food = False
                # We also always go for the food if we have less than 40 health.
                if snek['health_points'] < 40:
                    can_reach_food = True
            if not can_reach_food:
                continue

            # Update snek
            if path_length < snek_length:
                remainder = snek_length - path_length
                new_snek_coords = list(reversed(tentative_path)) + snek_coords[:remainder]
            else:
                new_snek_coords = list(reversed(tentative_path))[:snek_length]

            if grid[new_snek_coords[0][0]][new_snek_coords[0][1]] == FOOD:
                # we ate food so we grow
                new_snek_coords.append(new_snek_coords[-1])

            # Create a new grid with the updated snek positions
            new_grid = copy.deepcopy(grid)

            for coord in snek_coords:
                new_grid[coord[0]][coord[1]] = 0
            for coord in new_snek_coords:
                new_grid[coord[0]][coord[1]] = SNAKE

            foodtotail = a_star(food,new_snek_coords[-1],new_grid, new_snek_coords)
            if foodtotail:
                path = tentative_path
                break
            print "no path to tail from food"
        #end for food in foods

    # If we aren't going for the food, go for our own tail instead.
    if not path:
        # TODO: Don't just go for your own tail. Prefer to go closer to the middle.
        path = a_star(snek_head, snek['coords'][-1], grid, snek_coords)

    despair = not (path and len(path) > 1)
    if despair:
        for neighbour in neighbours(snek_head,grid,0,snek_coords, [1,2,5]):
            path = a_star(snek_head, neighbour, grid, snek_coords)
            #print 'i\'m scared'
            break
    despair = not (path and len(path) > 1)

    if despair:
        for neighbour in neighbours(snek_head,grid,0,snek_coords, [1,2]):
            path = a_star(snek_head, neighbour, grid, snek_coords)
            #print 'lik so scared'
            break

    if path:
        assert path[0] == tuple(snek_head)
        assert len(path) > 1

    return {
        'move': direction(path[0], path[1]),
        'taunt': "I'm a sneeky snek!"
    }


@bottle.post('/end')
def end():
    data = bottle.request.json
    return {
        'taunt': 'battlesnake-python!'
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()
if __name__ == '__main__':
    bottle.run(application, host=os.getenv('IP', '0.0.0.0'), port=os.getenv('PORT', '8080'))
