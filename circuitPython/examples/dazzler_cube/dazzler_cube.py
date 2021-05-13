# Port of the 'cube' Gameduino demo/example code from the Arduino environment, for the Dazzler Gameduino in CircuitPython
# Harvey.Vrsalovic , May 2021
#
#  This is more or less a "straight, naive" port from the C lang. and the Arduino libraries + Gameduino library into Python
#   It is intended to be a starting point for other code, and thus care was not taken for it to be optimized nor 100% exact to the
#   original code.
#  Also certain things were added that were not in the original C code,
#   like the Wii controller interface used on the Dazzler.
#
#

import bteve as eve
import math
import time

framenum = 0

P = 125
N = -P

CUBE_vertices = [
P,P,P,
N,P,P,
P,N,P,
N,N,P,

P,P,N,
N,P,N,
P,N,N,
N,N,N
]

def N_VERTICES():
    return int(len(CUBE_vertices) / 3)

# each line is a face: count, normal, 4 vertices
CUBE_faces = [
  4, 0,0,127,   0, 1, 3, 2,         #0
  4, 0,0,-127,  6, 7, 5, 4,         #8

  4, 0,127,0,   4, 5, 1, 0,         #16
  4, 0,-127,0,  2, 3, 7, 6,         #24

  4, 127,0,0,   0, 2, 6, 4,         #32
  4, -127,0,0,  3, 1, 5, 7,         #40

  -1                                #48
]

# 3D Projection

model_mat = [
  1.0, 0.0, 0.0,
  0.0, 1.0, 0.0,
  0.0, 0.0, 1.0
]

normal_mat = [
  1.0, 0.0, 0.0,
  0.0, 1.0, 0.0,
  0.0, 0.0, 1.0
]


def mult_matrices(a, b, c):
    result = [0] * 9
    for i in range(0,3):
        for j in range(0,3):
            idx = 3*i+j
            result[idx] = 0.0
            for k in range(0,3):
                result[idx] += a[3*i+k] * b[3*k+j]
    return result

def rotate(m, mi, angle, axis):
# (Based on glRotate())
# angle is a list of 3 elements, representing the vector <x,y,z> that's the axis of rotation
#   BE SURE THAT IT IS NORMALIZED (magnitude == 1)
# returns tuple of m, mi
#   3x3 rotation matrix in 'm'
#   and its inverse in 'mi'

    x = axis[0]
    y = axis[1]
    z = axis[2]

    s = math.sin(angle)
    c = math.cos(angle)

    xx = x*x*(1-c)
    xy = x*y*(1-c)
    xz = x*z*(1-c)
    yy = y*y*(1-c)
    yz = y*z*(1-c)
    zz = z*z*(1-c)

    xs = x * s
    ys = y * s
    zs = z * s

    m[0] = xx + c
    m[1] = xy - zs
    m[2] = xz + ys

    m[3] = xy + zs
    m[4] = yy + c
    m[5] = yz - xs

    m[6] = xz - ys
    m[7] = yz + xs
    m[8] = zz + c

    mi[0] = m[0]
    mi[1] = xy + zs
    mi[2] = xz - ys

    mi[3] = xy - zs
    mi[4] = m[4]
    mi[5] = yz + xs

    mi[6] = xz + ys
    mi[7] = yz - xs
    mi[8] = m[8]

    return m, mi

def rotation(angle, axis):
    global model_mat
    global normal_mat

    mat = [0] * 9
    mati = [0] * 9

    mat, mati = rotate(mat, mati, angle, axis)
    model_mat = mult_matrices(model_mat, mat, model_mat)
    normal_mat = mult_matrices(mati, normal_mat, normal_mat)

projected = [(0,0)] * N_VERTICES()

def project(gd):

    global CUBE_vertices
    global framenum

    pm = 0
    pm_e = len(CUBE_vertices)
    dst = 0

    # ORIGINAL LINE from C code:
    # scale = 64 * gd.h / 280

    # 280 makes the cube tiny on the Dazzler screen, so I changed it to 100
    # I don't understand this '100' divisor too well; If the number is too small however ( ~50 or so) , weird clipping is seen with the image
    #   it may be related to the >> 6   ( / 64) in the lines below where the actual projection occurs.  It possibly has to do with
    #   the size of the screen, though if that's the case, why the original code doesn't make this proportional to gd.w and gd.h in some way is unknown

    scale = 64 * gd.h / 100
    while pm < pm_e:
        x = int((scale * CUBE_vertices[pm])) >> 6
        pm += 1
        y = int((scale * CUBE_vertices[pm])) >> 6
        pm += 1
        z = int((scale * CUBE_vertices[pm])) >> 6
        pm += 1
        xx = x * model_mat[0] + y * model_mat[3] + z * model_mat[6]
        yy = x * model_mat[1] + y * model_mat[4] + z * model_mat[7]
        # ORIGINAL LINE, directly translated from C code: projected[dst] = (  (int((gd.w / 2 + xx)) << 4) , (int((gd.h / 2 + yy)) << 4) )
        # removed *16 mult (<< 4), as it seems the Dazzler's Vertex2f doesn't deal with subpixels like the other LCD based Gameduinos
        projected[dst] = ( (int((gd.w / 2 + xx))) ,  (int((gd.h / 2 + yy))) )
        dst += 1

def transform_normal(nx, ny, nz):
    global normal_mat
    xx = nx * normal_mat[0] + ny * normal_mat[1] + nz * normal_mat[2]
    yy = nx * normal_mat[3] + ny * normal_mat[4] + nz * normal_mat[5]
    zz = nx * normal_mat[6] + ny * normal_mat[7] + nz * normal_mat[8]
    return xx, yy, zz

def draw_quad(gd, x1, y1, x2, y2, x3, y3, bx1, by1, bx3, by3):

# Compute the fourth vertex of the parallelogram, (x4,y4)
    x4 = x3 + (x1 - x2)
    y4 = y3 + (y1 - y2)

# Apply Scissor to the extents of the quad
    minx = max(0,    min(min(x1, x2), min(x3, x4)))
    maxx = min(gd.w, max(max(x1, x2), max(x3, x4)))
    miny = max(0,    min(min(y1, y2), min(y3, y4)))
    maxy = min(gd.h, max(max(y1, y2), max(y3, y4)))
    gd.ScissorXY(minx, miny)
    gd.ScissorSize(maxx - minx, maxy - miny)

#  THIS IS FROM THE ORIGINAL CODE...
#   it *seems* to hack-together the "cmd_bitmap_transform" command via individual cmd writes to the BT8__ chip
#       (oy vey!)
## Set the new bitmap transform
#    # gd.c4(0xffffff21)
## bitmap transform
#    # gd.c4(x1 - minx)
#    # gd.c4(y1 - miny)
#    # gd.c4(x2 - minx)
#    # gd.c4(y2 - miny)
#    # gd.c4(x3 - minx)
#    # gd.c4(y3 - miny)

#    # gd.c4(bx1)
#    # gd.c4(by1)
#    # gd.c4(bx1)
#    # gd.c4(by3)
#    # gd.c4(bx3)
#    # gd.c4(by3)
#    # gd.c4(0)

#  Let's try to do it more officially, with the actual cmd_bitmap_transform:

    result_address = 0      # this probably isn't right...
    # the cmd_bitmap_transform just like a lot of other cmd_XXX places its result into a RAM location specified by this result address param.
    #   (actually, it's more like an offset from the beginning of the "user area" in RAM).  Location 0 is probably not correct but it doesn't seem
    #   to have any adverse effects in this case.  Perhaps if the code was doing more involved things and using up more RAM, this would have to
    #   be rethought

    # (int() coercions probably unnecessary)
    gd.cmd_bitmap_transform(
        int(x1 - minx),
        int(y1 - miny),
        int(x2 - minx),
        int(y2 - miny),
        int(x3 - minx),
        int(y3 - miny),
        int(bx1),
        int(by1),
        int(bx1),
        int(by3),
        int(bx3),
        int(by3),
        result_address)


# Draw the quad
    # ORIGINAL line from the C code version:
#   gd.Vertex2f(minx << 4, miny << 4)
# again, the Dazzler seems to not work with subpixels, so no *16 multiplys
    gd.Vertex2f(minx, miny)

def draw_faces(gd, dir, offset_x, offset_y):

    global CUBE_faces
    R = 5
    p = 0

    gd.BlendFunc(gd.ONE, gd.ONE_MINUS_SRC_ALPHA)
    gd.Begin(gd.BITMAPS)

    facen = 0
    n = CUBE_faces[p]
    while n != -1:
        facen += 1
        p += 1
        nx = CUBE_faces[p]
        p += 1
        ny = CUBE_faces[p]
        p += 1
        nz = CUBE_faces[p]
        p += 1

        v1 = CUBE_faces[p]
        v2 = CUBE_faces[p + 1]
        v3 = CUBE_faces[p + 2]
        p += n;
        n = CUBE_faces[p]

        x1 = projected[v1][0]
        y1 = projected[v1][1]
        x2 = projected[v2][0]
        y2 = projected[v2][1]
        x3 = projected[v3][0]
        y3 = projected[v3][1]
        area = (x1 - x3) * (y2 - y1) - (x1 - x2) * (y3 - y1)
        face = 1 if area < 0 else 0
        if face == dir:
            r = 20
            g = 20
            b = 80   # Ambient

            if face == 1:
                nx,ny,nz = transform_normal(nx, ny, nz)
                d = max(0, -nz)                      # diffuse light from +ve Z

                r += 2 * d
                g += 2 * d
                b += 2 * d

            gd.ColorRGB(min(255, int(r)), min(255, int(g)), min(255, int(b)))

            x1 = int(x1 /16)  + offset_x
            y1 = int(y1 /16)    +offset_y
            x2 = int(x2 /16)    +offset_x
            y2 = int(y2 /16)    +offset_y
            x3 = int(x3 /16)    +offset_x
            y3 = int(y3 /16)    +offset_y

            draw_quad(gd, x1, y1, x2, y2, x3, y3, -R, -R, 128 + R, 128 + R)


# this function is needed because rotate() function requires a normalized vector for
#   the axis of rotation in x,y,z
def normalize(vector):
    mag = 0
    for e in vector:
        mag += e*e
    if mag == 0:
        return vector, 0

    mag = math.sqrt(mag)
    for i in range(0,len(vector)):
        vector[i] = vector[i] / mag
    return vector, mag

def cube_main(gd):

    global framenum

    gd.cmd_loadimage(0, 0)
    gd.load(open("healsky3.jpg", "rb"))
    print("width = {0}, height = {1}".format(gd.w, gd.h))
    gd.BitmapHandle(0);
    gd.BitmapSize(gd.NEAREST, gd.BORDER, gd.BORDER, gd.w, gd.h);

    cx=gd.w//2
    cy=gd.h//2
    rx = 0
    ry = 0
    rz = 0

    while 1:
        framenum += 1
        cx = gd.w // 2
        cy = gd.h // 2
        
        rrx = 16
        rry = 16

        rx = 1 if rrx != 0 else 0
        ry = 1 if rry != 0 else 0
        rz = 1 if rrx !=0 and rry != 0 else 0

        rot_angle = 0.1
        if rrx < 0 or rry < 0:
            rot_angle = -0.1

        gd.Clear()
        norm_rot, magnitude = normalize([rx, ry, rz])
        if magnitude != 0:
            rotation(rot_angle, norm_rot)

        project(gd)
        draw_faces(gd, 0, cx, cy)
        draw_faces(gd, 1, cx, cy)
        gd.swap()

    print("exited")

if __name__ == "__main__":
    gd = eve.Brt_PicoEve_Module()
    gd.init()
    cube_main(gd)

