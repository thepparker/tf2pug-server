from entities import Pug, Server
from pprint import pprint

s = Server.Server("TF2")
p = Pug.Pug(pid = 1)

p.add_player(76561197960265729, "1", Pug.PlayerStats())
p.add_player(76561197960265730, "2", Pug.PlayerStats())
p.add_player(76561197960265731, "3", Pug.PlayerStats())

p.begin_game()

#pprint(p.game_stats)

s.reserve(p)
s.prepare()

log = s._log_interface

kill = 'L 10/01/2012 - 22:20:45: "1<0><[U:1:1]><Blue>" killed "2<2><[U:1:2]><Red>" with "scattergun" (attacker_position "-1803 129 236") (victim_position "-1767 278 218")'

log._dispatch_parse(kill)

pprint(p.game_stats)
