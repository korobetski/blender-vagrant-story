bl_info = {
    "name": "Vagrant Story file formats Add-on",
    "description": "Import-Export Vagrant Story file formats (WEP, SHP, SEQ, ZUD, MPD, ZND, P, FBT, FBC).",
    "author": "Sigfrid Korobetski (LunaticChimera)",
    "version": (2, 12),
    "blender": (3, 2, 0),
    "location": "File > Import-Export",
    "category": "Import-Export",
}

SIG = b"H01\x00"
VERTEX_RATIO = 128
def MDPToZND(mdpName):
    # http://datacrystal.romhacking.net/wiki/Vagrant_Story:rooms_list
    table = []
    table.append([])
    table.append([])
    table.append([])
    table.append([])
    table.append([])
    table.append([])
    table.append([])
    table.append([])
    table.append([])
    table.append(["MAP009.MPD", "MAP010.MPD", "MAP011.MPD", "MAP012.MPD", "MAP013.MPD", "MAP014.MPD", "MAP015.MPD", "MAP016.MPD", "MAP017.MPD",
                  "MAP018.MPD", "MAP019.MPD", "MAP020.MPD", "MAP021.MPD", "MAP022.MPD", "MAP023.MPD", "MAP024.MPD", "MAP027.MPD", "MAP409.MPD"])
    # 10 Ashley and Merlose outside the Wine Cellar gate
    table.append(["MAP211.MPD"])
    table.append(["MAP025.MPD"])
    table.append(["MAP026.MPD", "MAP408.MPD"])
    table.append(["MAP028.MPD", "MAP029.MPD", "MAP030.MPD", "MAP031.MPD", "MAP032.MPD", "MAP033.MPD", "MAP034.MPD", "MAP035.MPD", "MAP036.MPD",
                  "MAP037.MPD", "MAP038.MPD", "MAP039.MPD", "MAP040.MPD", "MAP041.MPD", "MAP042.MPD", "MAP043.MPD", "MAP044.MPD", "MAP045.MPD"])
    table.append(["MAP046.MPD"])  # 14
    table.append(["MAP047.MPD", "MAP048.MPD", "MAP049.MPD", "MAP050.MPD", "MAP051.MPD", "MAP052.MPD",
                  "MAP053.MPD", "MAP054.MPD", "MAP055.MPD", "MAP056.MPD", "MAP057.MPD", "MAP058.MPD", "MAP059.MPD"])  # 15
    table.append(["MAP060.MPD"])  # 16
    table.append(["MAP061.MPD"])  # 17
    table.append(["MAP062.MPD"])  # 18 Bardorba and Rosencrantz
    table.append(["MAP212.MPD"])  # 19 Ashley's flashback
    table.append(["MAP213.MPD"])  # 20 VKP briefing
    table.append(["MAP214.MPD"])  # 21 Ashley meets Merlose outside manor
    table.append(["MAP063.MPD", "MAP064.MPD", "MAP065.MPD", "MAP066.MPD", "MAP067.MPD",
                  "MAP068.MPD", "MAP069.MPD", "MAP070.MPD", "MAP071.MPD", "MAP072.MPD"])  # 22
    table.append(["MAP073.MPD", "MAP074.MPD", "MAP075.MPD",
                  "MAP076.MPD", "MAP077.MPD", "MAP078.MPD"])  # 23
    table.append(["MAP079.MPD", "MAP080.MPD", "MAP081.MPD", "MAP082.MPD", "MAP083.MPD", "MAP084.MPD", "MAP085.MPD", "MAP086.MPD",
                  "MAP087.MPD", "MAP088.MPD", "MAP089.MPD", "MAP090.MPD", "MAP091.MPD", "MAP092.MPD", "MAP093.MPD", "MAP094.MPD"])  # 24
    table.append(["MAP095.MPD", "MAP096.MPD", "MAP097.MPD",
                  "MAP098.MPD", "MAP099.MPD"])  # 25
    table.append(["MAP100.MPD"])  # 26 Ashley finds Sydney in the Cathedral
    table.append(["MAP101.MPD", "MAP102.MPD"])  # 27
    table.append(["MAP105.MPD", "MAP106.MPD", "MAP107.MPD", "MAP108.MPD", "MAP109.MPD", "MAP110.MPD", "MAP111.MPD", "MAP112.MPD", "MAP113.MPD",
                  "MAP114.MPD", "MAP115.MPD", "MAP116.MPD", "MAP117.MPD", "MAP118.MPD", "MAP119.MPD", "MAP120.MPD", "MAP121.MPD", "MAP122.MPD", "MAP123.MPD"])  # 28
    table.append(["MAP124.MPD", "MAP125.MPD", "MAP126.MPD",
                  "MAP127.MPD", "MAP128.MPD", "MAP129.MPD", "MAP130.MPD"])  # 29
    table.append(["MAP139.MPD", "MAP140.MPD", "MAP141.MPD",
                  "MAP142.MPD", "MAP143.MPD", "MAP144.MPD"])  # 30
    table.append(["MAP145.MPD", "MAP146.MPD"])
    table.append(["MAP147.MPD", "MAP148.MPD", "MAP149.MPD", "MAP150.MPD", "MAP151.MPD", "MAP152.MPD", "MAP153.MPD", "MAP154.MPD", "MAP155.MPD", "MAP156.MPD", "MAP157.MPD", "MAP158.MPD",
                  "MAP159.MPD", "MAP160.MPD", "MAP161.MPD", "MAP162.MPD", "MAP163.MPD", "MAP164.MPD", "MAP165.MPD", "MAP166.MPD", "MAP167.MPD", "MAP168.MPD", "MAP169.MPD", "MAP170.MPD"])
    # 33 Merlose finds corpses at Leà Monde's entrance
    table.append(["MAP172.MPD"])
    table.append(["MAP173.MPD"])  # 34 Dinas Walk
    table.append(["MAP174.MPD"])  # 35
    table.append(["MAP175.MPD"])  # 36 Gharmes Walk
    table.append(["MAP176.MPD"])  # 37
    table.append(["MAP177.MPD"])  # 38 The House Gilgitte
    table.append(["MAP171.MPD"])  # 39 Plateia Lumitar
    table.append(["MAP179.MPD", "MAP180.MPD", "MAP181.MPD", "MAP182.MPD", "MAP183.MPD", "MAP184.MPD", "MAP185.MPD", "MAP186.MPD", "MAP187.MPD", "MAP188.MPD", "MAP189.MPD", "MAP190.MPD", "MAP191.MPD",
                  "MAP192.MPD", "MAP193.MPD", "MAP194.MPD", "MAP195.MPD", "MAP196.MPD", "MAP197.MPD", "MAP198.MPD", "MAP199.MPD", "MAP200.MPD", "MAP201.MPD", "MAP202.MPD", "MAP203.MPD", "MAP204.MPD"])  # 40 Snowfly Forest
    # 41 Snowfly Forest East
    table.append(["MAP348.MPD", "MAP349.MPD", "MAP350.MPD"])
    table.append(["MAP205.MPD"])  # 42 Workshop "Work of Art"
    table.append(["MAP206.MPD"])  # 43 Workshop "Magic Hammer"
    table.append(["MAP207.MPD"])  # 44 Wkshop "Keane's Crafts"
    table.append(["MAP208.MPD"])  # 45 Workshop "Metal Works"
    table.append(["MAP209.MPD"])  # 46 Wkshop "Junction Point"
    table.append(["MAP210.MPD"])  # 47 Workshop "Godhands"
    table.append(["MAP220.MPD", "MAP221.MPD", "MAP222.MPD", "MAP223.MPD", "MAP224.MPD", "MAP225.MPD", "MAP226.MPD", "MAP227.MPD", "MAP228.MPD", "MAP229.MPD", "MAP230.MPD", "MAP231.MPD", "MAP232.MPD", "MAP233.MPD",
                  "MAP234.MPD", "MAP235.MPD", "MAP236.MPD", "MAP237.MPD", "MAP238.MPD", "MAP239.MPD", "MAP240.MPD", "MAP241.MPD", "MAP242.MPD", "MAP243.MPD", "MAP244.MPD", "MAP245.MPD", "MAP246.MPD"])  # 48 Undercity West
    table.append(["MAP247.MPD", "MAP248.MPD", "MAP249.MPD", "MAP250.MPD", "MAP251.MPD", "MAP252.MPD", "MAP253.MPD",
                  "MAP254.MPD", "MAP255.MPD", "MAP256.MPD", "MAP257.MPD", "MAP258.MPD", "MAP259.MPD"])  # 49 Undercity East
    table.append(["MAP260.MPD", "MAP261.MPD", "MAP262.MPD", "MAP263.MPD", "MAP264.MPD", "MAP265.MPD", "MAP266.MPD", "MAP267.MPD", "MAP268.MPD", "MAP269.MPD", "MAP270.MPD", "MAP271.MPD",
                  "MAP272.MPD", "MAP273.MPD", "MAP274.MPD", "MAP275.MPD", "MAP276.MPD", "MAP277.MPD", "MAP278.MPD", "MAP279.MPD", "MAP280.MPD", "MAP281.MPD", "MAP282.MPD", "MAP283.MPD"])  # 50
    table.append(["MAP284.MPD", "MAP285.MPD", "MAP286.MPD", "MAP287.MPD", "MAP288.MPD", "MAP289.MPD", "MAP290.MPD", "MAP291.MPD", "MAP292.MPD", "MAP293.MPD", "MAP294.MPD", "MAP295.MPD", "MAP296.MPD", "MAP297.MPD", "MAP298.MPD",
                  "MAP299.MPD", "MAP300.MPD", "MAP301.MPD", "MAP302.MPD", "MAP303.MPD", "MAP304.MPD", "MAP305.MPD", "MAP306.MPD", "MAP307.MPD", "MAP308.MPD", "MAP309.MPD", "MAP310.MPD", "MAP410.MPD", "MAP411.MPD"])  # 51 Abandoned Mines B2
    table.append(["MAP351.MPD", "MAP352.MPD", "MAP353.MPD", "MAP354.MPD",
                  "MAP355.MPD", "MAP356.MPD", "MAP357.MPD", "MAP358.MPD"])  # 52 Escapeway
    table.append(["MAP311.MPD", "MAP312.MPD", "MAP313.MPD", "MAP314.MPD", "MAP315.MPD", "MAP316.MPD", "MAP317.MPD", "MAP318.MPD", "MAP319.MPD", "MAP320.MPD", "MAP321.MPD", "MAP322.MPD", "MAP323.MPD", "MAP324.MPD", "MAP325.MPD", "MAP326.MPD", "MAP327.MPD",
                  "MAP328.MPD", "MAP329.MPD", "MAP330.MPD", "MAP331.MPD", "MAP332.MPD", "MAP333.MPD", "MAP334.MPD", "MAP335.MPD", "MAP336.MPD", "MAP337.MPD", "MAP338.MPD", "MAP339.MPD", "MAP340.MPD", "MAP341.MPD", "MAP342.MPD"])  # 53 Limestone Quarry
    table.append(["MAP343.MPD", "MAP344.MPD", "MAP345.MPD",
                  "MAP346.MPD", "MAP347.MPD"])  # 54
    table.append([])  # 55
    for i in range(359, 382):
        table[55].append("MAP"+str(i)+".MPD")
    table.append([])  # 56
    for i in range(382, 408):
        table[56].append("MAP"+str(i)+".MPD")
    table.append(["MAP103.MPD"])
    table.append(["MAP104.MPD"])
    table.append(["MAP413.MPD"])
    table.append(["MAP131.MPD"])  # 60
    table.append(["MAP132.MPD"])
    table.append(["MAP133.MPD"])
    table.append(["MAP134.MPD"])
    table.append(["MAP135.MPD"])
    table.append(["MAP136.MPD"])
    table.append(["MAP137.MPD"])
    table.append(["MAP138.MPD"])
    table.append(["MAP178.MPD"])
    table.append(["MAP414.MPD"])
    table.append(["MAP415.MPD"])  # 70
    for i in range(0, 25):
        table.append([])
    table.append(["MAP427.MPD"])  # 96
    table.append(["MAP428.MPD"])  # 97
    table.append(["MAP429.MPD"])  # 98
    table.append(["MAP430.MPD"])  # 99
    table.append(["MAP000.MPD"])  # 100
    for i in range(0, 149):
        table.append([])
    table.append(["MAP506.MPD"])  # 250

    for i in range(0, len(table)):
        for j in range(0, len(table[i])):
            if mdpName == table[i][j]:
                ZNDId = str(i)
                if len(ZNDId) < 3:
                    ZNDId = "0"+ZNDId
                if len(ZNDId) < 3:
                    ZNDId = "0"+ZNDId
                return "ZONE"+ZNDId+".ZND"

    return "ZONE032.ZND"
