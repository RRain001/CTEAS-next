c-----------------------------------------------------------------------
      program p7i_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7I FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7i_source_anchor.py: QATR and TFAC.
c
c --- Input on stdin, list directed:
c     line 1: mode  1 = QATR matrix, 2 = TFAC matrix
c     mode 1: icase icode xl xu eps ndim   (icode selects the integrand)
c     mode 2: icase x xbegin xend xspace npoints
c             followed by npoints rows: at(1,i) at(2,i)
c     Output: icase value status (status only for QATR)
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'const.puf'
      include 'ctpass.puf'
c
      integer mode,ios,icase,icode,ndim,ier
      real xl,xu,eps,y
      real th,tl,tu
      integer icodg, i, npts
      real aux1(200)
      real xx, xbeginin, xendin, xspacein
      real xr, yr, ang, xp, yp
      common/icodeg/icodg
      external fctsel
c
c --- /CONST/ values are normally set by the vendor BLOCK DATA unit, which is
c     not part of the extracted subset, so the ones TFAC needs are set here.
      zero=0.0
      one=1.0
      half=0.5
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7I oracle: missing mode'
c
      if(mode.eq.3)then
 40      read(*,*,iostat=ios) icase,xr,yr,ang
         if(ios.ne.0) goto 999
         call rotate(xr,yr,ang,xp,yp)
         write(*,'(i8,2(1x,es20.12))') icase,xp,yp
         goto 40
      endif
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,icode,xl,xu,eps,ndim
         if(ios.ne.0) goto 999
         icodg=icode
         call qatr(xl,xu,eps,ndim,fctsel,y,ier,aux1)
         write(*,'(i8,1x,es20.12,1x,i4)') icase,y,ier
         goto 10
      endif
c
 20   continue
      read(*,*,iostat=ios) icase,xx,xbeginin,xendin,xspacein,npts
      if(ios.ne.0) goto 999
      xbegin=xbeginin
      xend=xendin
      xspace=xspacein
      do 30 i=1,npts
         read(*,*,iostat=ios) at(1,i),at(2,i)
         if(ios.ne.0) stop 'P7I oracle: missing terrain factor row'
 30   continue
      call tfac(xx,th,tl,tu)
      write(*,'(i8,3(1x,es20.12))') icase,th,tl,tu
      goto 20
c
 999  continue
      end
c-----------------------------------------------------------------------
      function fctsel(x)
c-----------------------------------------------------------------------
c --- Integrands selected by the global ICodG, mirroring the C++ test set.
      include 'params.puf'
      common/icodeg/icodg
      if(icodg.eq.1)then
         fctsel=sin(x)
      elseif(icodg.eq.2)then
         fctsel=x*x
      elseif(icodg.eq.3)then
         fctsel=exp(-x)
      elseif(icodg.eq.4)then
         fctsel=0.0
      elseif(icodg.eq.5)then
         fctsel=1.0
      else
         fctsel=0.0
      endif
      return
      end
