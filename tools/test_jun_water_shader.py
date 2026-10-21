"""Compile/render the production GLSL in a hidden WGL window, never the game.

Checks the water join and isolation from ordinary textured primitives using
synthetic textures. No gameplay inputs, screenshots or save files are touched.
"""
import ast
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    user, gdi, gl = c.windll.user32, c.windll.gdi32, c.windll.opengl32
    user.CreateWindowExW.restype = w.HWND
    user.CreateWindowExW.argtypes = [w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,c.c_int,c.c_int,c.c_int,c.c_int,w.HWND,w.HMENU,w.HINSTANCE,c.c_void_p]
    user.GetDC.argtypes = [w.HWND]; user.GetDC.restype = w.HDC
    user.ReleaseDC.argtypes = [w.HWND,w.HDC]
    user.DestroyWindow.argtypes = [w.HWND]
    hwnd = user.CreateWindowExW(0,'STATIC','Jun shader check',0,0,0,64,64,None,None,None,None)
    assert hwnd
    dc = user.GetDC(hwnd)
    # PIXELFORMATDESCRIPTOR (40 bytes), RGBA/OpenGL window surface.
    class PFD(c.Structure):
        _fields_ = [('size',w.WORD),('version',w.WORD),('flags',w.DWORD),
                    ('channels',c.c_ubyte*20),('layerMask',w.DWORD),
                    ('visibleMask',w.DWORD),('damageMask',w.DWORD)]
    pfd=PFD();pfd.size=40;pfd.version=1;pfd.flags=0x24
    pfd.channels[1]=24
    gdi.ChoosePixelFormat.argtypes=[w.HDC,c.POINTER(PFD)]
    gdi.SetPixelFormat.argtypes=[w.HDC,c.c_int,c.POINTER(PFD)]
    assert gdi.SetPixelFormat(dc,gdi.ChoosePixelFormat(dc,c.byref(pfd)),c.byref(pfd))
    gl.wglCreateContext.argtypes=[w.HDC];gl.wglCreateContext.restype=c.c_void_p
    gl.wglMakeCurrent.argtypes=[w.HDC,c.c_void_p]
    gl.wglDeleteContext.argtypes=[c.c_void_p]
    ctx=gl.wglCreateContext(dc);assert ctx and gl.wglMakeCurrent(dc,ctx)
    gl.wglGetProcAddress.argtypes=[c.c_char_p];gl.wglGetProcAddress.restype=c.c_void_p
    def proc(name,result,*args):
        ptr=gl.wglGetProcAddress(name.encode())
        if ptr not in (None,1,2,3,c.c_void_p(-1).value):
            return c.WINFUNCTYPE(result,*args)(ptr)
        fn=getattr(gl,name);fn.restype=result;fn.argtypes=list(args);return fn
    U,I,F,P=c.c_uint,c.c_int,c.c_float,c.c_void_p
    try:
        source=(ROOT/'psxrecomp/runtime/src/gpu_gl_renderer.c').read_text()
        create=proc('glCreateShader',U,U)
        shader_source=proc('glShaderSource',None,U,I,c.POINTER(c.c_char_p),P)
        compile_shader=proc('glCompileShader',None,U)
        shader_iv=proc('glGetShaderiv',None,U,U,c.POINTER(I))
        shader_log=proc('glGetShaderInfoLog',None,U,I,P,P)
        shaders=[]
        for name,kind in [('TEX_VS',0x8b31),('TEX_FS',0x8b30)]:
            block=source.split('static const char *'+name+' =',1)[1].split(';\n',1)[0]
            code=''.join(ast.literal_eval(s) for s in re.findall(r'"(?:\\.|[^"\\])*"',block)).encode()
            sh=create(kind);ptr=c.c_char_p(code);shader_source(sh,1,c.byref(ptr),None);compile_shader(sh)
            ok=I();shader_iv(sh,0x8b81,c.byref(ok));log=c.create_string_buffer(8192)
            shader_log(sh,len(log),None,log);assert ok.value,log.value
            shaders.append(sh)
        program=proc('glCreateProgram',U)()
        for sh in shaders:proc('glAttachShader',None,U,U)(program,sh)
        bind_out=proc('glBindFragDataLocationIndexed',None,U,U,U,c.c_char_p)
        bind_out(program,0,0,b'frag');bind_out(program,0,1,b'blend_factor')
        proc('glLinkProgram',None,U)(program)
        ok=I();proc('glGetProgramiv',None,U,U,c.POINTER(I))(program,0x8b82,c.byref(ok))
        log=c.create_string_buffer(8192);proc('glGetProgramInfoLog',None,U,I,P,P)(program,len(log),None,log)
        assert ok.value,log.value
        proc('glUseProgram',None,U)(program)
        loc=proc('glGetUniformLocation',I,U,c.c_char_p)
        def ui(name,val):proc('glUniform1i',None,I,I)(loc(program,name.encode()),val)
        def uf(name,val):proc('glUniform1f',None,I,F)(loc(program,name.encode()),val)
        for name,val in [('u_xhalf',32),('u_xscale',1)]:uf(name,val)
        ui('u_semipass',0);ui('u_semimode',-1)
        samplers=['u_vram','u_hd_background','u_hd_ground','u_hd_skin','u_hd_xiaoyu',
                  'u_hd_anna','u_hd_kuma','u_hd_eddy','u_hd_julia','u_hd_heihachi',
                  'u_jun_background','u_jun_ground']
        gen=proc('glGenTextures',None,I,c.POINTER(U));bind=proc('glBindTexture',None,U,U)
        tex=proc('glTexImage2D',None,U,I,I,I,I,I,U,U,P)
        param=proc('glTexParameteri',None,U,U,I)
        for unit,name in enumerate(samplers):
            ui(name,unit);proc('glActiveTexture',None,U)(0x84c0+unit)
            ident=U();gen(1,c.byref(ident));bind(0x0de1,ident)
            param(0x0de1,0x2801,0x2600);param(0x0de1,0x2800,0x2600)
            if unit==0:
                pixels=(c.c_ushort*(1024*512))(*([0x7fff]*(1024*512)))
                tex(0x0de1,0,0x8234,1024,512,0,0x8d94,0x1403,pixels)
            else:
                rgba=(181,158,206,255) if name=='u_jun_ground' else (80,100,130,255)
                pixels=(c.c_ubyte*(64*64*4))(*(rgba*(64*64)))
                tex(0x0de1,0,0x8058,64,64,0,0x1908,0x1401,pixels)
                proc('glGenerateMipmap',None,U)(0x0de1)
        vao=U();proc('glGenVertexArrays',None,I,c.POINTER(U))(1,c.byref(vao))
        proc('glBindVertexArray',None,U)(vao)
        vbo=U();proc('glGenBuffers',None,I,c.POINTER(U))(1,c.byref(vbo))
        proc('glBindBuffer',None,U,U)(0x8892,vbo)
        vertices=(F*6)(0,0,128,0,0,1024)
        proc('glBufferData',None,U,c.c_ssize_t,P,U)(0x8892,c.sizeof(vertices),vertices,0x88e4)
        proc('glVertexAttribPointer',None,U,I,U,c.c_ubyte,I,P)(0,2,0x1406,0,0,None)
        proc('glEnableVertexAttribArray',None,U)(0)
        attr1=proc('glVertexAttrib1f',None,U,F)
        attr2=proc('glVertexAttrib2f',None,U,F,F)
        attr4=proc('glVertexAttrib4f',None,U,F,F,F,F)
        attr1(5,2);attr4(7,0,0,255,255)
        proc('glViewport',None,I,I,I,I)(0,0,64,64)
        def render(kind,v,shade):
            attr1(11,kind);attr2(10,.5,v);attr4(2,shade,shade,shade,1)
            proc('glDrawArrays',None,U,I,I)(4,0,3)
            pixel=(c.c_ubyte*4)()
            proc('glReadPixels',None,I,I,I,I,U,U,P)(16,16,1,1,0x1908,0x1401,pixel)
            return tuple(pixel[:3])
        water=(181,158,206)
        for shade in (.3,.4,.5):
            assert render(11,1,shade)==water
            assert render(10,1,shade)==water
        assert render(10,.8,.5)==(80,100,130), 'Upper scenery must not be recoloured'
        native=render(0,1,.3)
        assert all(abs(x-153)<=1 for x in native),native
        assert render(3,1,.3)==(48,60,78), 'Character modulation must remain intact'
        print('PASS: production GLSL compiles/links; water join agrees across lighting; native/skin shading preserved')
    finally:
        gl.wglMakeCurrent(None,None);gl.wglDeleteContext(ctx)
        user.ReleaseDC(hwnd,dc);user.DestroyWindow(hwnd)


if __name__=='__main__':main()
