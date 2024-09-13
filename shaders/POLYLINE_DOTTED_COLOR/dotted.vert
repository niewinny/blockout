
void main()
{
    v_Color = color;
    v_Pos = pos;
    v_Length = lineLength;

    vec2 normalizedPos = pos / viewportSize * 2.0 - 1.0;
    gl_Position = vec4(normalizedPos, 0.0, 1.0);
}
