// sample_cs.hlsl
// Compute shader: load texel from src at integer coords px,py and write packed RGBA8 into UAV
Texture2D<float4> src : register(t0);
RWByteAddressBuffer dst : register(u0);

cbuffer Push : register(b0)
{
    uint px;
    uint py;
    uint width;
    uint height;
};

[numthreads(1,1,1)]
void main(uint3 id : SV_DispatchThreadID)
{
    float4 c = src.Load(int3(px, py, 0));
    uint r = (uint)(saturate(c.r) * 255.0f) & 0xff;
    uint g = (uint)(saturate(c.g) * 255.0f) & 0xff;
    uint b = (uint)(saturate(c.b) * 255.0f) & 0xff;
    uint packed = r | (g << 8) | (b << 16);
    dst.Store(0, packed);
}
